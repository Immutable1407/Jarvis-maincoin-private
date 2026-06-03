from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .config_mi import STATE_DIR

LANE_FEEDBACK_NAME = "lane_feedback.jsonl"
GUARDIAN_COOLDOWN_NAME = "guardian_exit_cooldowns.json"

_REASON_COOLDOWNS_SECONDS = {
    "local_stop": 4 * 60 * 60,
    "breakeven": 2 * 60 * 60,
    "trailing": 60 * 60,
}


def _now(now_ts: float | None = None) -> float:
    return float(time.time() if now_ts is None else now_ts)


def _direction_from_position(p: dict) -> str:
    if p.get("posSide") in {"long", "short"}:
        return str(p.get("posSide"))
    try:
        return "long" if float(p.get("pos") or 0) > 0 else "short"
    except Exception:
        return ""


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                out.append(row)
        except json.JSONDecodeError:
            continue
    return out


def _parse_reason(reason: str) -> str | None:
    r = str(reason or "").lower()
    if "tp2" in r or "partial_tp_2" in r or "mfe" in r:
        return None
    if "local_stop" in r:
        return "local_stop"
    if "breakeven" in r:
        return "breakeven"
    if "trailing" in r:
        return "trailing"
    return None


def lane_feedback_allows_near_miss(
    strategy_lane: str,
    inst_id: str | None = None,
    side: str | None = None,
    *,
    now_ts: float | None = None,
    lookback_seconds: int = 48 * 60 * 60,
) -> tuple[bool, str]:
    """Conservative v1.4 near-miss feedback gate.

    The loosening path fails closed if the feedback file/dir is unavailable.
    Recent negative lane samples or repeated same instrument+side local stops
    disable near-miss for the lane/candidate while full-threshold trades remain eligible.
    """
    if not STATE_DIR.exists():
        return False, "lane_feedback_unavailable"
    feedback_path = STATE_DIR / LANE_FEEDBACK_NAME
    if not feedback_path.exists():
        return False, "lane_feedback_unavailable"
    rows = _read_jsonl(feedback_path)
    cutoff = _now(now_ts) - float(lookback_seconds)
    negative = 0
    local_stop_same = 0
    for row in rows[-500:]:
        lane = row.get("strategy_lane") or row.get("lane")
        if lane != strategy_lane:
            continue
        ts = row.get("ts_epoch") or row.get("time") or row.get("timestamp")
        if ts is not None:
            try:
                if float(ts) < cutoff:
                    continue
            except Exception:
                pass
        try:
            if float(row.get("realized_net_pct", row.get("net_pct", 0.0)) or 0.0) < 0:
                negative += 1
        except Exception:
            pass
        reason = _parse_reason(str(row.get("exit_reason") or row.get("reason") or ""))
        if reason == "local_stop" and inst_id and side and row.get("instId") == inst_id and row.get("direction") == side:
            local_stop_same += 1
    if negative > 0:
        return False, "recent_negative_lane_sample"
    if local_stop_same >= 2:
        return False, "same_instrument_side_local_stop_repeats"
    return True, "lane_feedback_allows_near_miss"


def correlate_same_direction_governor(
    positions: list[dict],
    signal: Any,
    cfg: Any,
    *,
    equity: float | None,
    new_size: Any | None = None,
) -> tuple[bool, dict]:
    side = getattr(signal, "side", None)
    same = [p for p in (positions or []) if _direction_from_position(p) == side]
    aggregate_margin = 0.0
    aggregate_notional = 0.0
    for p in same:
        for key in ("margin", "imr", "initialMargin", "marginUsd"):
            try:
                aggregate_margin += float(p.get(key) or 0.0)
                break
            except Exception:
                continue
        try:
            aggregate_notional += abs(float(p.get("notionalUsd") or p.get("notional") or 0.0))
        except Exception:
            pass
    if new_size is not None:
        try:
            aggregate_margin += float(getattr(new_size, "margin", 0.0) or 0.0)
        except Exception:
            pass
        try:
            aggregate_notional += float(getattr(new_size, "notional", 0.0) or 0.0)
        except Exception:
            pass
    aggregate_estimated_risk_pct = (aggregate_margin / float(equity)) if equity else 0.0
    detail = {
        "same_direction_count": len(same),
        "aggregate_margin": round(aggregate_margin, 6),
        "aggregate_notional": round(aggregate_notional, 6),
        "aggregate_estimated_risk_pct": round(aggregate_estimated_risk_pct, 6),
        "candidate_score": float(getattr(signal, "score", 0.0) or 0.0),
        "strategy_lane": getattr(signal, "strategy_lane", None),
    }
    if not same:
        detail["reason"] = "no_same_direction_exposure"
        return True, detail
    high_quality = detail["candidate_score"] >= float(getattr(cfg, "correlated_add_min_score", 84.0)) or detail["strategy_lane"] == "trend_confirmed"
    if high_quality:
        detail["reason"] = "high_quality_same_direction_addition"
        return True, detail
    detail["reason"] = "correlated_same_direction_low_quality_addition"
    return False, detail


def _cooldown_path() -> Path:
    return STATE_DIR / GUARDIAN_COOLDOWN_NAME


def _load_cooldowns() -> dict:
    try:
        raw = json.loads(_cooldown_path().read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _save_cooldowns(data: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _cooldown_path().write_text(json.dumps(data, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def record_guardian_exit_cooldown(inst_id: str, direction: str, reason: str, *, now_ts: float | None = None) -> dict:
    reason_key = _parse_reason(reason)
    if not reason_key:
        return {"recorded": False, "reason": "no_penalty_exit"}
    data = _load_cooldowns()
    key = f"{inst_id}|{direction}"
    data[key] = {"last_exit_ts": _now(now_ts), "cooldown_reason": reason_key, "raw_reason": reason}
    _save_cooldowns(data)
    return {"recorded": True, "key": key, **data[key]}


def guardian_cooldown_allows_entry(inst_id: str, direction: str, *, now_ts: float | None = None) -> tuple[bool, dict]:
    data = _load_cooldowns()
    row = data.get(f"{inst_id}|{direction}") or {}
    reason = row.get("cooldown_reason")
    if reason not in _REASON_COOLDOWNS_SECONDS:
        return True, {"reason": "no_guardian_cooldown"}
    elapsed = _now(now_ts) - float(row.get("last_exit_ts") or 0.0)
    remaining = float(_REASON_COOLDOWNS_SECONDS[reason]) - elapsed
    if remaining > 0:
        return False, {"reason": "guardian_exit_cooldown", "cooldown_reason": reason, "remaining_seconds": round(remaining, 1)}
    return True, {"reason": "guardian_cooldown_expired", "cooldown_reason": reason}
