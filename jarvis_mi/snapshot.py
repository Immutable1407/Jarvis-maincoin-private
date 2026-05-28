from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from .config_mi import DATA_DIR, ensure_dirs

def save_snapshot(payload: dict) -> str:
    ensure_dirs()
    now = datetime.now(timezone.utc)
    d = DATA_DIR / 'snapshots' / now.strftime('%Y%m%d')
    d.mkdir(parents=True, exist_ok=True)
    p = d / (now.strftime('%H%M%S') + '.json')
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return str(p)
