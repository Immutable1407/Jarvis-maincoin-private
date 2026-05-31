from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import json
from jarvis_mi.account_guard import assert_mi_account
from jarvis_mi.config_mi import MiConfig, ensure_dirs
from jarvis_mi.fills import sync_fills
from jarvis_mi.okx_mi_client import OKXMiClient

if __name__ == "__main__":
    try:
        ensure_dirs()
        cfg = MiConfig.from_env()
        client = OKXMiClient(cfg)
        assert_mi_account(client, cfg)
        result = sync_fills(client, cfg)
        if result.get("count"):
            print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"event":"ERROR","where":"mi_sync_fills","error":str(e)}, ensure_ascii=False))
        raise
