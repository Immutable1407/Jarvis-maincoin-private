from __future__ import annotations
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
        sig = evaluate_inst(inst_id, h1_by_inst[inst_id], m15_by_inst[inst_id], btc_bias)
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
        rec = {"event": "NO_TRADE", "reason": "no_v1_1_candidate", "signals": [s.__dict__ for s in signals], **base_snapshot}
        rec["snapshot"] = save_snapshot({**base_snapshot, "signals": [s.__dict__ for s in signals], "decision": rec})
        append_jsonl("decisions.jsonl", rec)
        return rec

    selected = candidates[0]
    ok, portfolio_reasons = portfolio_allows_entry(
        positions,
        selected,
        cfg.active_max_positions,
        cfg.enable_second_position,
        allow_mixed_direction_portfolio=cfg.allow_mixed_direction_portfolio,
    )
    if not ok:
        rec = {"event": "NO_TRADE", "reason": "portfolio_gate", "portfolio_reasons": portfolio_reasons, "selected": selected.__dict__, **base_snapshot}
        rec["snapshot"] = save_snapshot({**base_snapshot, "signals": [s.__dict__ for s in signals], "decision": rec})
        append_jsonl("decisions.jsonl", rec)
        return rec

    m15 = m15_by_inst[selected.inst_id]
    vol_pct = (atr(m15, 14)[-1] / selected.entry_ref) if selected.entry_ref and len(m15) >= 20 else 0.0
    risk_decision = decide_risk(market_state, selected.score, vol_pct, equity, recent_stopouts=0, resonance_risk_multiplier=resonance.risk_multiplier)
    if risk_decision.risk_mode == "paused":
        rec = {"event": "NO_TRADE", "reason": "risk_engine_paused", "selected": selected.__dict__, "risk_decision": risk_decision.to_dict(), **base_snapshot}
        rec["snapshot"] = save_snapshot({**base_snapshot, "signals": [s.__dict__ for s in signals], "decision": rec})
        append_jsonl("decisions.jsonl", rec)
        return rec

    trade = execute_entry(client, cfg, instruments[selected.inst_id], selected, equity, risk_decision=risk_decision, positions=positions)
    rec = {"event": "TRADE_ATTEMPTED", "selected": selected.__dict__, "risk_decision": risk_decision.to_dict(), "trade": trade, **base_snapshot}
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
