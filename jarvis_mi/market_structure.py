from __future__ import annotations

"""Deterministic v2 market-structure classifier for Hermes Mi.

Pure Python, no network/LLM. It consumes existing candle lists plus optional
market_state/resonance objects and fails closed to WAIT on malformed input.
"""

from dataclasses import dataclass, asdict
from typing import Any


def _num(v: Any, default: float = 0.0) -> float:
    try:
        if v in (None, ""):
            return default
        return float(v)
    except Exception:
        return default


def candle_value(candle: Any, key: str) -> float:
    """Robust candle access for project dicts and OKX list shapes.

    Dict keys may be c/h/l/o or close/high/low/open. OKX arrays are usually
    [ts, o, h, l, c, ...].
    """
    if isinstance(candle, dict):
        aliases = {
            "o": ("o", "open"),
            "h": ("h", "high"),
            "l": ("l", "low"),
            "c": ("c", "close", "last"),
        }.get(key, (key,))
        for k in aliases:
            if k in candle:
                return _num(candle.get(k))
        return 0.0
    if isinstance(candle, (list, tuple)):
        idx = {"o": 1, "h": 2, "l": 3, "c": 4}.get(key)
        if idx is not None and len(candle) > idx:
            return _num(candle[idx])
    return 0.0


def _series(candles: list[Any], key: str) -> list[float]:
    return [candle_value(x, key) for x in candles if candle_value(x, key) > 0]


def _ema(values: list[float], n: int) -> list[float]:
    if not values:
        return []
    k = 2.0 / (n + 1.0)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _atr_pct(candles: list[Any], period: int = 14) -> float:
    if len(candles) < 2:
        return 0.0
    trs: list[float] = []
    prev_c = candle_value(candles[0], "c")
    for x in candles[1:]:
        h, l, c = candle_value(x, "h"), candle_value(x, "l"), candle_value(x, "c")
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
        prev_c = c
    recent = trs[-period:] if len(trs) >= period else trs
    price = candle_value(candles[-1], "c")
    return (sum(recent) / len(recent) / price) if recent and price else 0.0


def _cross_count(fast: list[float], slow: list[float], lookback: int = 24) -> int:
    n = min(len(fast), len(slow), lookback + 1)
    if n < 2:
        return 0
    f, s = fast[-n:], slow[-n:]
    count = 0
    prev = f[0] >= s[0]
    for i in range(1, n):
        cur = f[i] >= s[i]
        if cur != prev:
            count += 1
        prev = cur
    return count


@dataclass(frozen=True)
class MarketStructure:
    structure_regime: str  # trend | transition | chop | wait
    structure_confidence: int
    trend_direction: str  # long | short | both | none
    reason_codes: list[str]
    range_quality_score: int
    trend_persistence_score: int
    false_breakout_risk_score: int

    def to_dict(self) -> dict:
        return asdict(self)


WAIT_STRUCTURE = MarketStructure("wait", 0, "none", ["classifier_wait_default"], 0, 0, 100)


class MarketStructureClassifier:
    def classify(self, candles_by_inst: dict[str, list[Any]], market_state: Any = None, resonance: Any = None) -> MarketStructure:
        try:
            if not candles_by_inst:
                return WAIT_STRUCTURE
            per_inst = []
            range_scores = []
            false_scores = []
            reasons: list[str] = []
            for inst, candles in candles_by_inst.items():
                if not candles or len(candles) < 50:
                    reasons.append(f"{inst}:insufficient_candles")
                    continue
                closes = _series(candles, "c")
                highs = _series(candles, "h")
                lows = _series(candles, "l")
                if len(closes) < 50:
                    continue
                e20, e50 = _ema(closes, 20), _ema(closes, 50)
                price = closes[-1]
                slope20 = (e20[-1] - e20[-6]) / price if price and len(e20) >= 6 else 0.0
                spread = (e20[-1] - e50[-1]) / price if price else 0.0
                persist_long = sum(1 for c, a, b in zip(closes[-12:], e20[-12:], e50[-12:]) if c > a > b)
                persist_short = sum(1 for c, a, b in zip(closes[-12:], e20[-12:], e50[-12:]) if c < a < b)
                direction = "long" if persist_long >= 8 and slope20 > 0 else "short" if persist_short >= 8 and slope20 < 0 else "none"
                persistence = int(max(persist_long, persist_short) / 12 * 100)
                crosses = _cross_count(e20, e50, 30)
                recent_h, recent_l = max(highs[-48:]), min(lows[-48:])
                width = (recent_h - recent_l) / price if price else 0.0
                atrp = _atr_pct(candles)
                boundary_clarity = max(0, min(100, int((width / max(atrp, 0.0001)) * 18)))
                range_quality = max(0, min(100, boundary_clarity - crosses * 10 - (20 if width > 0.08 else 0)))
                upper_reentry = highs[-1] >= recent_h * 0.998 and closes[-1] < recent_h * 0.994
                lower_reentry = lows[-1] <= recent_l * 1.002 and closes[-1] > recent_l * 1.006
                false_risk = min(100, crosses * 18 + (35 if upper_reentry or lower_reentry else 0) + (20 if persistence < 50 else 0))
                per_inst.append((inst, direction, persistence, slope20, spread, crosses))
                range_scores.append(range_quality)
                false_scores.append(false_risk)

            if not per_inst:
                return MarketStructure("wait", 0, "none", reasons + ["no_valid_candles"], 0, 0, 100)

            long_votes = sum(1 for x in per_inst if x[1] == "long")
            short_votes = sum(1 for x in per_inst if x[1] == "short")
            aligned = max(long_votes, short_votes)
            trend_dir = "long" if long_votes > short_votes else "short" if short_votes > long_votes else "both" if aligned else "none"
            trend_persistence = int(sum(x[2] for x in per_inst) / len(per_inst))
            avg_range = int(sum(range_scores) / len(range_scores)) if range_scores else 0
            avg_false = int(sum(false_scores) / len(false_scores)) if false_scores else 100
            align_score = int(aligned / len(per_inst) * 100)
            cross_avg = sum(x[5] for x in per_inst) / len(per_inst)

            ms_bias = getattr(market_state, "direction_bias", None) if market_state is not None else None
            ms_budget = getattr(market_state, "risk_budget", None) if market_state is not None else None
            if ms_bias == "no_trade" or ms_budget == "zero":
                return MarketStructure("wait", 15, "none", reasons + ["market_state_no_trade"], avg_range, trend_persistence, max(avg_false, 90))

            resonance_adj = float(getattr(resonance, "score_adjustment", 0.0) or 0.0) if resonance is not None else 0.0
            if aligned >= 2 and trend_persistence >= 62 and avg_false <= 55 and cross_avg <= 2.5:
                conf = min(100, max(55, int(0.5 * trend_persistence + 0.35 * align_score + resonance_adj)))
                regime = "trend" if conf >= 62 else "transition"
                reasons.append(f"trend_votes_{trend_dir}_{aligned}")
            elif avg_range >= 58 and trend_persistence < 65 and avg_false <= 75:
                conf = min(100, max(45, avg_range - int(cross_avg * 4)))
                regime = "chop"
                trend_dir = "none"
                reasons.append("high_quality_range_chop")
            elif trend_persistence >= 45 or aligned >= 1:
                conf = min(80, max(35, int((trend_persistence + align_score) / 2)))
                regime = "transition"
                reasons.append("forming_or_decaying_trend")
            else:
                conf = 25
                regime = "wait"
                trend_dir = "none"
                reasons.append("low_structure_edge")
            return MarketStructure(regime, conf, trend_dir, reasons, avg_range, trend_persistence, avg_false)
        except Exception as exc:
            return MarketStructure("wait", 0, "none", ["classifier_error", type(exc).__name__], 0, 0, 100)
