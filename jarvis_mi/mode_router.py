from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ModeDecision:
    mode: str  # WAIT | CHOP | TRANSITION | TREND
    allow_trend_confirmed_normal: bool
    allow_trend_probe: bool
    allow_range_swing: bool
    allow_second_position: bool
    max_leverage: int
    max_loss_pct: float
    risk_tier: str
    mode_reason_codes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


WAIT_MODE = ModeDecision("WAIT", False, False, False, False, 0, 0.0, "wait", ["router_wait_default"])


class ModeRouter:
    def route(self, structure: Any, wear: Any = None, drawdown_pct: float = 0.0) -> ModeDecision:
        try:
            regime = str(getattr(structure, "structure_regime", "wait") or "wait").lower()
            conf = int(getattr(structure, "structure_confidence", 0) or 0)
            range_q = int(getattr(structure, "range_quality_score", 0) or 0)
            persist = int(getattr(structure, "trend_persistence_score", 0) or 0)
            false_risk = int(getattr(structure, "false_breakout_risk_score", 100) or 100)
            wear_level = int(getattr(wear, "wear_level", 0) or 0) if wear is not None else 0
            reasons = list(getattr(structure, "reason_codes", []) or []) + list(getattr(wear, "reason_codes", []) or [])

            if regime == "wait" or conf < 30:
                return ModeDecision("WAIT", False, False, False, False, 0, 0.0, "wait", reasons + ["router_wait_regime"])

            if regime == "chop":
                allow_range = range_q >= 70 and conf >= 55 and false_risk <= 75
                return ModeDecision(
                    "CHOP", False, False, allow_range, False,
                    5 if allow_range else 0, 0.01 if allow_range else 0.0,
                    "range_conservative" if allow_range else "wait",
                    reasons + (["router_chop_range_only"] if allow_range else ["router_chop_wait_default"]),
                )

            if regime == "transition":
                if wear_level >= 3:
                    return ModeDecision("WAIT", False, False, False, False, 0, 0.0, "wear_block", reasons + ["wear_level_3_blocks_transition"])
                return ModeDecision("TRANSITION", False, True, False, False, 6, 0.015, "probe", reasons + ["router_transition_probe_only"])

            if regime == "trend":
                if wear_level >= 3:
                    return ModeDecision("WAIT", False, False, False, False, 0, 0.0, "wear_block", reasons + ["wear_level_3_blocks_trend"])
                normal = conf >= 62 and persist >= 60 and false_risk <= 60 and wear_level <= 1
                max_lev = 10 if normal else 6
                max_loss = 0.025 if normal else 0.012
                if wear_level == 2:
                    normal = False
                    reasons.append("wear_level_2_demotes_trend")
                return ModeDecision("TREND", normal, True, False, normal and wear_level == 0, max_lev, max_loss, "trend_normal" if normal else "probe", reasons + ["router_trend"])

            return WAIT_MODE
        except Exception as exc:
            return ModeDecision("WAIT", False, False, False, False, 0, 0.0, "wait", ["router_error", type(exc).__name__])
