from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from .market_structure import candle_value


@dataclass(frozen=True)
class ConfirmationDecision:
    allow_normal: bool
    allow_probe: bool
    reason_codes: list[str]
    confirmation_score: int

    def to_dict(self) -> dict:
        return asdict(self)


class SecondConfirmationGate:
    def evaluate(self, signal: Any, structure: Any, candles: list[Any] | None = None, resonance: Any = None, explicit_confirmed: bool = False) -> ConfirmationDecision:
        try:
            lane = getattr(signal, "strategy_lane", "") or ""
            side = getattr(signal, "side", None)
            regime = str(getattr(structure, "structure_regime", "wait") or "wait")
            conf = int(getattr(structure, "structure_confidence", 0) or 0)
            persist = int(getattr(structure, "trend_persistence_score", 0) or 0)
            false_risk = int(getattr(structure, "false_breakout_risk_score", 100) or 100)
            reasons: list[str] = []
            if lane != "trend_confirmed":
                return ConfirmationDecision(False, True, ["confirmation_not_required_for_probe_or_range"], 0)
            if regime != "trend":
                return ConfirmationDecision(False, regime == "transition", [f"confirmation_blocks_normal_in_{regime}"], 20)
            if not side:
                return ConfirmationDecision(False, False, ["confirmation_no_side"], 0)
            score = 0
            if explicit_confirmed:
                score += 40; reasons.append("explicit_confirmation")
            if conf >= 70:
                score += 20; reasons.append("structure_confidence_ok")
            if persist >= 70:
                score += 20; reasons.append("trend_persistence_ok")
            if false_risk <= 45:
                score += 20; reasons.append("false_breakout_risk_low")
            candles = candles or []
            if len(candles) >= 6:
                closes = [candle_value(x, "c") for x in candles]
                highs = [candle_value(x, "h") for x in candles]
                lows = [candle_value(x, "l") for x in candles]
                if side == "long":
                    prev_high = max(highs[-6:-2])
                    persisted = closes[-1] > prev_high and closes[-2] > prev_high * 0.998
                    no_reentry = min(closes[-3:]) > prev_high * 0.995
                else:
                    prev_low = min(lows[-6:-2])
                    persisted = closes[-1] < prev_low and closes[-2] < prev_low * 1.002
                    no_reentry = max(closes[-3:]) < prev_low * 1.005
                if persisted:
                    score += 25; reasons.append("breakout_persisted_bars")
                if no_reentry:
                    score += 15; reasons.append("no_fast_range_reentry")
            allowed = score >= 60 or (conf >= 82 and persist >= 78 and false_risk <= 35)
            if not allowed:
                reasons.append("first_breakout_needs_second_confirmation")
            return ConfirmationDecision(allowed, True, reasons, min(100, score))
        except Exception as exc:
            return ConfirmationDecision(False, False, ["confirmation_error", type(exc).__name__], 0)
