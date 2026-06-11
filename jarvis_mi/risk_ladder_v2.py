from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class RiskDecisionV2:
    leverage: int
    margin_pct: float
    max_loss_pct: float
    risk_mode: str
    reason_codes: list[str]
    max_positions: int
    risk_tier: str

    def to_dict(self) -> dict:
        return asdict(self)


class RiskLadderV2:
    def decide(self, mode: Any, lane: str = "trend_confirmed", *, second_confirmation: bool = False, drawdown_pct: float = 0.0, wear_level: int = 0) -> RiskDecisionV2:
        try:
            m = str(getattr(mode, "mode", mode) or "WAIT").upper()
            reasons = list(getattr(mode, "mode_reason_codes", []) or [])
            if m == "WAIT":
                return RiskDecisionV2(0, 0.0, 0.0, "paused", reasons + ["risk_wait_no_entries"], 0, "wait")
            if m == "CHOP":
                if lane != "range_swing" or not getattr(mode, "allow_range_swing", False):
                    return RiskDecisionV2(0, 0.0, 0.0, "paused", reasons + ["risk_chop_range_only"], 0, "wait")
                lev, margin, loss, pos, tier, rmode = 4, 0.08, 0.007, 1, "range_conservative", "range"
            elif m == "TRANSITION":
                if lane == "trend_confirmed":
                    return RiskDecisionV2(0, 0.0, 0.0, "paused", reasons + ["risk_transition_blocks_normal"], 0, "wait")
                lev, margin, loss, pos, tier, rmode = 5, 0.07, 0.010, 1, "probe", "probe"
            elif m == "TREND":
                if lane == "trend_confirmed" and second_confirmation and getattr(mode, "allow_trend_confirmed_normal", False):
                    lev, margin, loss, pos, tier, rmode = 9, 0.18, 0.022, 2, "trend_normal", "normal"
                elif lane == "trend_probe" and getattr(mode, "allow_trend_probe", False):
                    lev, margin, loss, pos, tier, rmode = 6, 0.09, 0.012, 1, "probe", "probe"
                else:
                    return RiskDecisionV2(0, 0.0, 0.0, "paused", reasons + ["risk_trend_lane_not_allowed"], 0, "wait")
            else:
                return RiskDecisionV2(0, 0.0, 0.0, "paused", reasons + ["risk_unknown_mode"], 0, "wait")

            if drawdown_pct <= -0.03:
                lev = min(lev, 5); margin *= 0.65; loss *= 0.65; pos = min(pos, 1); reasons.append("drawdown_override_reduced")
            if wear_level >= 2:
                lev = min(lev, 5); margin *= 0.55; loss *= 0.55; pos = min(pos, 1); reasons.append("wear_override_reduced")
            elif wear_level == 1:
                lev = max(3, min(lev, lev - 1)); margin *= 0.8; loss *= 0.8; reasons.append("wear_level_1_reduced")

            max_lev = int(getattr(mode, "max_leverage", lev) or lev)
            max_loss = float(getattr(mode, "max_loss_pct", loss) or loss)
            lev = min(lev, max_lev)
            loss = min(loss, max_loss)
            return RiskDecisionV2(int(lev), round(margin, 4), round(loss, 4), rmode, reasons + [f"v2_lane_{lane}"], pos, tier)
        except Exception as exc:
            return RiskDecisionV2(0, 0.0, 0.0, "paused", ["risk_ladder_v2_error", type(exc).__name__], 0, "wait")
