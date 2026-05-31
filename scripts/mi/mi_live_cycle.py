from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import json
from jarvis_mi.account_guard import assert_mi_account
from jarvis_mi.config_mi import MiConfig, ensure_dirs
from jarvis_mi.ledger import append_jsonl
from jarvis_mi.okx_mi_client import OKXMiClient
from jarvis_mi.signal_score import evaluate_inst, btc_bias_from_h1
from jarvis_mi.execution import execute_entry
from jarvis_mi.market_state import classify_market_state
from jarvis_mi.resonance import compute_resonance
from jarvis_mi.risk_engine import decide_risk
from jarvis_mi.portfolio import portfolio_allows_entry
from jarvis_mi.snapshot import save_snapshot
from jarvis_mi.indicators import atr
from jarvis_mi.sizing import compute_size


def lane_profit_gate(selected, risk_decision, preview_size, equity, cfg, resonance_adjustment: float = 0.0) -> tuple[bool, dict]:
    """v1.3 lane-aware expected-profit gate.

    Full-trade expected net must normally clear the lane threshold. A controlled
    near-miss path is allowed only for high-score candidates with fee-positive
    TP1 economics, preserving v1.2's cost discipline while allowing more live
    samples in a 50U account where contract granularity causes threshold cliffs.
    """
    stop_pct = abs(selected.entry_ref - selected.stop) / selected.entry_ref if selected.entry_ref else 0.0
    expected_trade_gross = preview_size.notional * stop_pct * float(selected.expected_r or 0.0)
    expected_roundtrip_fee = preview_size.notional * float(cfg.taker_fee_rate) * 2.0
    expected_trade_net = expected_trade_gross - expected_roundtrip_fee
    expected_trade_net_pct = expected_trade_net / equity if equity else 0.0
    tp1_r = float(getattr(selected, "tp1_r", 1.2) or 1.2)
    tp1_fraction = float(getattr(selected, "tp1_fraction", 0.5) or 0.5)
    expected_tp1_net = preview_size.notional * stop_pct * tp1_r * tp1_fraction - preview_size.notional * float(cfg.taker_fee_rate) * (1.0 + tp1_fraction)
    expected_tp1_net_pct = expected_tp1_net / equity if equity else 0.0
    lane = getattr(selected, "strategy_lane", "trend_confirmed") or "trend_confirmed"
    lane_thresholds = getattr(cfg, "lane_min_expected_net_profit_pct", None) or {}
    base_threshold = max(float(cfg.min_expected_net_profit_pct), float(cfg.altcoin_profit_baseline_pct) * float(cfg.maincoin_profit_baseline_multiplier))
    min_net_pct = float(lane_thresholds.get(lane, base_threshold))
    passed = expected_trade_net_pct >= min_net_pct
    near_miss_floor = min_net_pct * float(getattr(cfg, "near_miss_profit_gate_ratio", 0.92))
    near_miss = (
        not passed
        and expected_trade_net_pct >= near_miss_floor
        and expected_tp1_net_pct >= float(getattr(cfg, "min_tp1_net_profit_pct", 0.0015))
        and float(getattr(selected, "score", 0.0) or 0.0) >= float(getattr(cfg, "near_miss_min_score", 66.0))
        and float(resonance_adjustment or 0.0) >= float(getattr(cfg, "near_miss_min_resonance_adjustment", 0.0))
        and getattr(risk_decision, "risk_mode", "") != "paused"
    )
    if near_miss:
        passed = True
    preview = {
        "expected_trade_net": round(expected_trade_net, 4),
        "expected_trade_net_pct": round(expected_trade_net_pct, 5),
        "expected_tp1_net": round(expected_tp1_net, 4),
        "expected_tp1_net_pct": round(expected_tp1_net_pct, 5),
        "min_net_pct": round(min_net_pct, 5),
        "base_min_net_pct": round(base_threshold, 5),
        "near_miss_floor_pct": round(near_miss_floor, 5),
        "lane": lane,
        "near_miss_pass": near_miss,
        "gate_version": "v1.3.0",
        "sizing": preview_size.__dict__,
    }
    return passed, preview


def run_live_cycle() -> dict:
    ensure_dirs()
    cfg = MiConfig.from_env()
    client = OKXMiClient(cfg)
    acct = assert_mi_account(client, cfg)
    equity = client.usdt_equity()
    positions = client.open_positions()
    non_mi = [p for p in positions if p.get("instId") not in cfg.allowed_insts]
    if non_mi:
        raise RuntimeError(f"non-whitelist SWAP positions present: {[p.get('instId') for p in non_mi]}")
    instruments = client.instruments()
    missing = [x for x in cfg.allowed_insts if x not in instruments]
    if missing:
        raise RuntimeError(f"missing instruments: {missing}")

    h1_by_inst = {}
    m15_by_inst = {}
    for inst_id in cfg.allowed_insts:
        h1_by_inst[inst_id] = client.candles(inst_id, "1H", 120)
        m15_by_inst[inst_id] = client.candles(inst_id, "15m", 120)

    btc_h1 = h1_by_inst["BTC-USDT-SWAP"]
    btc_bias = btc_bias_from_h1(btc_h1)
    market_state = classify_market_state(
        btc_h1,
        h1_by_inst.get("ETH-USDT-SWAP"),
        h1_by_inst.get("SOL-USDT-SWAP"),
        h1_by_inst.get("BNB-USDT-SWAP"),
    )
    resonance = compute_resonance(h1_by_inst)

    base_snapshot = {
        "account": acct,
        "equity": equity,
        "positions": [{"instId": p.get("instId"), "pos": p.get("pos"), "posSide": p.get("posSide"), "upl": p.get("upl")} for p in positions],
        "btc_bias": btc_bias,
        "market_state": market_state.to_dict(),
        "resonance": resonance.to_dict(),
    }

    if len(positions) >= cfg.active_max_positions:
        rec = {"event": "NO_TRADE", "reason": "active_max_positions_reached", **base_snapshot}
        rec["snapshot"] = save_snapshot({**base_snapshot, "decision": rec})
        append_jsonl("decisions.jsonl", rec)
        return rec
    if market_state.direction_bias == "no_trade" or market_state.risk_budget == "zero":
        rec = {"event": "NO_TRADE", "reason": "market_state_blocks_new_entries", **base_snapshot}
        rec["snapshot"] = save_snapshot({**base_snapshot, "decision": rec})
        append_jsonl("decisions.jsonl", rec)
        return rec

    signals = []
    for inst_id in cfg.allowed_insts:
        sig = evaluate_inst(inst_id, h1_by_inst[inst_id], m15_by_inst[inst_id], btc_bias, cfg=cfg)
        if sig.side == "long" and market_state.direction_bias == "short_only":
            sig.side = None; sig.reason.append("market_state_blocks_long")
        if sig.side == "short" and market_state.direction_bias == "long_only":
            sig.side = None; sig.reason.append("market_state_blocks_short")
        if sig.side:
            sig.score += resonance.score_adjustment
            sig.reason.extend(resonance.reason_codes)
        signals.append(sig)

    candidates = [s for s in signals if s.side]
    candidates.sort(key=lambda s: s.score, reverse=True)
    if not candidates:
        rec = {"event": "NO_TRADE", "reason": "no_candidate", "signals": [s.__dict__ for s in signals], **base_snapshot}
        rec["snapshot"] = save_snapshot({**base_snapshot, "signals": [s.__dict__ for s in signals], "decision": rec})
        append_jsonl("decisions.jsonl", rec)
        return rec

    rejected_candidates = []
    for selected in candidates:
        ok, portfolio_reasons = portfolio_allows_entry(
            positions,
            selected,
            cfg.active_max_positions,
            cfg.enable_second_position,
            allow_mixed_direction_portfolio=cfg.allow_mixed_direction_portfolio,
        )
        if not ok:
            rejected_candidates.append({"reason": "portfolio_gate", "portfolio_reasons": portfolio_reasons, "selected": selected.__dict__})
            continue

        m15 = m15_by_inst[selected.inst_id]
        vol_pct = (atr(m15, 14)[-1] / selected.entry_ref) if selected.entry_ref and len(m15) >= 20 else 0.0
        risk_decision = decide_risk(market_state, selected.score, vol_pct, equity, recent_stopouts=0, resonance_risk_multiplier=resonance.risk_multiplier, strategy_lane=getattr(selected, "strategy_lane", "trend_confirmed"))
        if risk_decision.risk_mode == "paused":
            rec = {"event": "NO_TRADE", "reason": "risk_engine_paused", "selected": selected.__dict__, "risk_decision": risk_decision.to_dict(), **base_snapshot}
            rec["snapshot"] = save_snapshot({**base_snapshot, "signals": [s.__dict__ for s in signals], "decision": rec})
            append_jsonl("decisions.jsonl", rec)
            return rec

        # v1.2.0 percent baseline: maincoin per-trade expected net profit should scale with equity
        # and exceed the altcoin dynamic baseline by multiplier, instead of using fixed 0.5U.
        inst = instruments[selected.inst_id]
        preview_size = compute_size(
            equity=equity,
            price=selected.entry_ref,
            stop=selected.stop,
            ct_val=inst["ctVal"],
            lot_sz=inst["lotSz"],
            min_sz=inst["minSz"],
            leverage=int(risk_decision.leverage),
            margin_pct=float(risk_decision.margin_pct),
            max_loss_pct=float(risk_decision.max_loss_pct),
        )
        profit_gate_ok, profit_preview = lane_profit_gate(
            selected, risk_decision, preview_size, equity, cfg,
            resonance_adjustment=float(getattr(resonance, "score_adjustment", 0.0) or 0.0),
        )
        if not profit_gate_ok:
            rejected_candidates.append({"reason": "lane_profit_gate_not_met", "selected": selected.__dict__, "risk_decision": risk_decision.to_dict(), "profit_preview": profit_preview})
            continue

        trade = execute_entry(client, cfg, instruments[selected.inst_id], selected, equity, risk_decision=risk_decision, positions=positions)
        rec = {"event": "TRADE_ATTEMPTED", "selected": selected.__dict__, "risk_decision": risk_decision.to_dict(), "profit_preview": profit_preview, "trade": trade, **base_snapshot}
        rec["snapshot"] = save_snapshot({**base_snapshot, "signals": [s.__dict__ for s in signals], "decision": rec})
        append_jsonl("decisions.jsonl", rec)
        return rec

    rec = {"event": "NO_TRADE", "reason": "all_candidates_rejected", "rejected_candidates": rejected_candidates[:8], "signals": [s.__dict__ for s in signals], **base_snapshot}
    rec["snapshot"] = save_snapshot({**base_snapshot, "signals": [s.__dict__ for s in signals], "decision": rec})
    append_jsonl("decisions.jsonl", rec)
    return rec


if __name__ == "__main__":
    try:
        result = run_live_cycle()
        if result.get("event") == "TRADE_ATTEMPTED":
            print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"event": "ERROR", "where": "mi_live_cycle", "error": str(e)}, ensure_ascii=False))
        raise
