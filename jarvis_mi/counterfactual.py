from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any

from .config_mi import DATA_DIR


@dataclass(frozen=True)
class CounterfactualRecord:
    ts: str
    kind: str
    inst_id: str | None
    side: str | None
    lane: str | None
    reason: str
    mode: str | None = None
    regime: str | None = None
    candidate_score: float | None = None
    details: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class CounterfactualEvaluator:
    """Safe cold-path ledger for v2-blocked candidates.

    Writes only JSONL under data/mi/ledgers by default. Tests can pass temp dirs.
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR
        self.ledger_dir = self.data_dir / "ledgers"
        self.snapshot_dir = self.data_dir / "counterfactuals"

    def record_blocked(self, signal: Any, reason: str, *, mode: Any = None, structure: Any = None, details: dict | None = None) -> dict:
        rec = CounterfactualRecord(
            ts=datetime.now(timezone.utc).isoformat(),
            kind="blocked_candidate",
            inst_id=getattr(signal, "inst_id", None) or getattr(signal, "instId", None),
            side=getattr(signal, "side", None),
            lane=getattr(signal, "strategy_lane", None),
            reason=reason,
            mode=getattr(mode, "mode", None) if mode is not None else None,
            regime=getattr(structure, "structure_regime", None) if structure is not None else None,
            candidate_score=float(getattr(signal, "score", 0.0) or 0.0),
            details=details or {},
        ).to_dict()
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        path = self.ledger_dir / "counterfactuals.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        return rec

    def summarize(self, limit: int = 200) -> dict:
        path = self.ledger_dir / "counterfactuals.jsonl"
        if not path.exists():
            return {"blocked_total": 0, "by_reason": {}, "by_lane": {}, "sample": []}
        rows: list[dict] = []
        for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        by_reason: dict[str, int] = {}
        by_lane: dict[str, int] = {}
        for r in rows:
            by_reason[str(r.get("reason") or "unknown")] = by_reason.get(str(r.get("reason") or "unknown"), 0) + 1
            by_lane[str(r.get("lane") or "unknown")] = by_lane.get(str(r.get("lane") or "unknown"), 0) + 1
        return {"blocked_total": len(rows), "by_reason": by_reason, "by_lane": by_lane, "sample": rows[-5:]}


def summarize_counterfactuals(data_dir: Path | None = None, limit: int = 200) -> dict:
    return CounterfactualEvaluator(data_dir=data_dir).summarize(limit=limit)
