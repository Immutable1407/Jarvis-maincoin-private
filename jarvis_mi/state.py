from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .config_mi import STATE_DIR, ensure_dirs


def state_path(name: str) -> Path:
    ensure_dirs()
    return STATE_DIR / name


def load_json(name: str, default: Any) -> Any:
    p = state_path(name)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(name: str, data: Any) -> None:
    p = state_path(name)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
