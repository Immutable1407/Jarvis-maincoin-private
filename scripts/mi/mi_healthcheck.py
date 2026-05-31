from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import json
from jarvis_mi.account_guard import assert_mi_account
from jarvis_mi.config_mi import MiConfig, ensure_dirs
from jarvis_mi.ledger import append_jsonl
from jarvis_mi.okx_mi_client import OKXMiClient


def run_healthcheck() -> dict:
    ensure_dirs()
    cfg = MiConfig.from_env()
    client = OKXMiClient(cfg)
    acct = assert_mi_account(client, cfg)
    equity = client.usdt_equity()
    positions = client.open_positions()
    bad = [p.get("instId") for p in positions if p.get("instId") not in cfg.allowed_insts]
    instruments = client.instruments()
    missing = [x for x in cfg.allowed_insts if x not in instruments]
    ok = equity > 0 and not bad and not missing
    rec = {"event": "HEALTHCHECK", "ok": ok, "account": acct, "equity": equity, "positions": [{"instId": p.get("instId"), "pos": p.get("pos"), "posSide": p.get("posSide"), "upl": p.get("upl")} for p in positions], "bad_positions": bad, "missing_instruments": missing}
    append_jsonl("healthcheck.jsonl", rec)
    return rec


if __name__ == "__main__":
    try:
        r = run_healthcheck()
        if not r.get("ok"):
            print(json.dumps(r, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"event": "ERROR", "where": "mi_healthcheck", "error": str(e)}, ensure_ascii=False))
        raise
