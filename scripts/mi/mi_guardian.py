from __future__ import annotations
import json
from jarvis_mi.account_guard import assert_mi_account, assert_allowed_inst
from jarvis_mi.config_mi import MiConfig, ensure_dirs
from jarvis_mi.execution import reduce_only_close
from jarvis_mi.indicators import atr
from jarvis_mi.ledger import append_jsonl
from jarvis_mi.okx_mi_client import OKXMiClient


def run_guardian() -> dict:
    ensure_dirs()
    cfg = MiConfig.from_env()
    client = OKXMiClient(cfg)
    acct = assert_mi_account(client, cfg)
    positions = client.open_positions()
    events = []
    for p in positions:
        inst_id = p.get("instId")
        assert_allowed_inst(inst_id, cfg)
        pos = float(p.get("pos") or 0)
        direction = "long" if (p.get("posSide") == "long" or pos > 0) else "short"
        avg_px = float(p.get("avgPx") or p.get("bePx") or 0)
        mark = float(p.get("markPx") or p.get("last") or 0)
        m15 = client.candles(inst_id, "15m", 60)
        if not m15 or not mark:
            continue
        recent_low = min(x["l"] for x in m15[-8:-1])
        recent_high = max(x["h"] for x in m15[-8:-1])
        a = atr(m15, 14)[-1]
        reason = None
        if direction == "long":
            local_stop = min(recent_low, avg_px - 1.2 * a) if avg_px else recent_low
            if mark <= local_stop:
                reason = f"guardian_local_stop_long mark={mark} stop={local_stop}"
        else:
            local_stop = max(recent_high, avg_px + 1.2 * a) if avg_px else recent_high
            if mark >= local_stop:
                reason = f"guardian_local_stop_short mark={mark} stop={local_stop}"
        if reason:
            events.append(reduce_only_close(client, cfg, p, reason))
    rec = {"event": "GUARDIAN", "account": acct, "positions": len(positions), "actions": events}
    append_jsonl("guardian.jsonl", rec)
    return rec


if __name__ == "__main__":
    try:
        r = run_guardian()
        if r.get("actions"):
            print(json.dumps(r, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"event": "ERROR", "where": "mi_guardian", "error": str(e)}, ensure_ascii=False))
        raise
