from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from .market_structure import candle_value


@dataclass(frozen=True)
class RangeDecision:
    allow: bool
    reason_codes: list[str]
    boundary: str = "none"
    expected_edge_pct: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class LimitedRangeSurviveEngine:
    def evaluate(self, signal: Any, structure: Any, candles: list[Any] | None = None, *, fee_rate: float = 0.0005, cooldown_active: bool = False, crash_or_squeeze: bool = False) -> RangeDecision:
        try:
            if cooldown_active:
                return RangeDecision(False, ["range_cooldown_active"])
            if crash_or_squeeze:
                return RangeDecision(False, ["range_crash_or_squeeze_block"])
            if getattr(signal, "strategy_lane", "") != "range_swing":
                return RangeDecision(False, ["not_range_swing_lane"])
            if getattr(structure, "structure_regime", "") != "chop":
                return RangeDecision(False, ["range_only_in_chop"])
            q = int(getattr(structure, "range_quality_score", 0) or 0)
            if q < 70:
                return RangeDecision(False, ["range_quality_too_low"])
            candles = candles or []
            price = float(getattr(signal, "entry_ref", 0.0) or 0.0)
            if len(candles) >= 30 and price:
                hi = max(candle_value(x, "h") for x in candles[-48:])
                lo = min(candle_value(x, "l") for x in candles[-48:])
            else:
                stop = float(getattr(signal, "stop", 0.0) or 0.0)
                width = abs(price - stop) * 3.0
                hi = price + width / 2
                lo = price - width / 2
            width = hi - lo
            if width <= 0 or price <= 0:
                return RangeDecision(False, ["range_invalid_width"])
            lower_zone = lo + width * 0.24
            upper_zone = hi - width * 0.24
            side = getattr(signal, "side", None)
            boundary = "none"
            if side == "long" and price <= lower_zone:
                boundary = "lower"
            elif side == "short" and price >= upper_zone:
                boundary = "upper"
            else:
                return RangeDecision(False, ["price_not_near_range_boundary"])
            gross_edge = (width * 0.35) / price
            expected_edge = gross_edge - fee_rate * 2.5
            if expected_edge < 0.003:
                return RangeDecision(False, ["fee_adjusted_edge_too_small"], boundary, expected_edge)
            return RangeDecision(True, ["range_boundary_edge_ok"], boundary, expected_edge)
        except Exception as exc:
            return RangeDecision(False, ["range_engine_error", type(exc).__name__])
