from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from .config_mi import LEDGER_DIR, ensure_dirs


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_jsonl(name: str, record: dict[str, Any]) -> None:
    ensure_dirs()
    path = LEDGER_DIR / name
    rec = {"ts": utc_now(), **record}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")


def emit(event: str, **kwargs: Any) -> None:
    append_jsonl("events.jsonl", {"event": event, **kwargs})
