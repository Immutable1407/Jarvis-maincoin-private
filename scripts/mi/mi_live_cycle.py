from __future__ import annotations
import json
from jarvis_mi.account_guard import assert_mi_account
from jarvis_mi.config_mi import MiConfig, ensure_dirs
from jarvis_mi.ledger import append_jsonl
from jarvis_mi.okx_mi_client import OKXMiClient
from jarvis_mi.signal_score import evaluate_inst, btc_bias_from_h1
from jarvis_mi.execution import execute_entry


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
    if len(positions) >= cfg.max_positions:
        rec = {"event": "NO_TRADE", "reason": "max_positions_reached", "account": acct, "equity": equity, "positions": [{"instId": p.get("instId"), "pos": p.get("pos"), "posSide": p.get("posSide")} for p in positions]}
        append_jsonl("decisions.jsonl", rec)
        return rec
    instruments = client.instruments()
    missing = [x for x in cfg.allowed_insts if x not in instruments]
    if missing:
        raise RuntimeError(f"missing instruments: {missing}")
    btc_h1 = client.candles("BTC-USDT-SWAP", "1H", 120)
    btc_bias = btc_bias_from_h1(btc_h1)
    signals = []
    for inst_id in cfg.allowed_insts:
        h1 = btc_h1 if inst_id == "BTC-USDT-SWAP" else client.candles(inst_id, "1H", 120)
        m15 = client.candles(inst_id, "15m", 120)
        sig = evaluate_inst(inst_id, h1, m15, btc_bias)
        signals.append(sig)
    candidates = [s for s in signals if s.side]
    candidates.sort(key=lambda s: s.score, reverse=True)
    if not candidates:
        rec = {"event": "NO_TRADE", "reason": "no_v0_1_candidate", "account": acct, "equity": equity, "btc_bias": btc_bias, "signals": [s.__dict__ for s in signals]}
        append_jsonl("decisions.jsonl", rec)
        return rec
    selected = candidates[0]
    trade = execute_entry(client, cfg, instruments[selected.inst_id], selected, equity)
    rec = {"event": "TRADE_ATTEMPTED", "account": acct, "equity": equity, "btc_bias": btc_bias, "selected": selected.__dict__, "trade": trade}
    append_jsonl("decisions.jsonl", rec)
    return rec


if __name__ == "__main__":
    try:
        result = run_live_cycle()
        # no stdout for normal no-trade; stdout only when order/error so local cron stays quiet.
        if result.get("event") == "TRADE_ATTEMPTED":
            print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"event": "ERROR", "where": "mi_live_cycle", "error": str(e)}, ensure_ascii=False))
        raise
