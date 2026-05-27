from __future__ import annotations
from dataclasses import dataclass
from .indicators import ema, atr


@dataclass
class Signal:
    inst_id: str
    side: str | None
    score: float
    reason: list[str]
    entry_ref: float
    stop: float
    expected_r: float


def evaluate_inst(inst_id: str, h1: list[dict[str, float]], m15: list[dict[str, float]], btc_bias: str | None) -> Signal:
    if len(h1) < 60 or len(m15) < 80:
        return Signal(inst_id, None, 0, ["insufficient_candles"], 0, 0, 0)
    h1c = [x["c"] for x in h1]
    m15c = [x["c"] for x in m15]
    e20 = ema(h1c, 20)
    e50 = ema(h1c, 50)
    m_e20 = ema(m15c, 20)
    a15 = atr(m15, 14)
    last = h1[-1]
    mlast = m15[-1]
    price = mlast["c"]
    atrv = a15[-1]
    recent_high = max(x["h"] for x in m15[-8:-1])
    recent_low = min(x["l"] for x in m15[-8:-1])
    side = None
    reasons: list[str] = []
    score = 0.0
    stop = 0.0
    h1_bull = last["c"] > e20[-1] > e50[-1] and e20[-1] > e20[-4]
    h1_bear = last["c"] < e20[-1] < e50[-1] and e20[-1] < e20[-4]
    m_break_long = price > m_e20[-1] and (price > recent_high or (m15[-2]["c"] < m_e20[-2] and price > m_e20[-1]))
    m_break_short = price < m_e20[-1] and (price < recent_low or (m15[-2]["c"] > m_e20[-2] and price < m_e20[-1]))
    if h1_bull and m_break_long:
        side = "long"
        score = 70
        reasons += ["h1_bull", "m15_long_trigger"]
        stop = min(recent_low, price - 1.2 * atrv)
        if btc_bias == "bear" and inst_id != "BTC-USDT-SWAP":
            score -= 20
            reasons.append("btc_against")
        if btc_bias == "bull":
            score += 5
            reasons.append("btc_aligned")
    elif h1_bear and m_break_short:
        side = "short"
        score = 70
        reasons += ["h1_bear", "m15_short_trigger"]
        stop = max(recent_high, price + 1.2 * atrv)
        if btc_bias == "bull" and inst_id != "BTC-USDT-SWAP":
            score -= 20
            reasons.append("btc_against")
        if btc_bias == "bear":
            score += 5
            reasons.append("btc_aligned")
    else:
        reasons.append("no_v0_1_trigger")
    if side:
        risk = abs(price - stop) / price
        expected_r = 1.5 if risk > 0 else 0
        if risk < 0.0015:
            score -= 10
            reasons.append("stop_too_tight")
        if risk > 0.025:
            score -= 15
            reasons.append("stop_too_wide")
    else:
        expected_r = 0
    return Signal(inst_id, side if score >= 65 else None, score, reasons, price, stop, expected_r)


def btc_bias_from_h1(h1: list[dict[str, float]]) -> str | None:
    if len(h1) < 60:
        return None
    c = [x["c"] for x in h1]
    e20 = ema(c, 20)
    e50 = ema(c, 50)
    last = c[-1]
    if last > e20[-1] > e50[-1]:
        return "bull"
    if last < e20[-1] < e50[-1]:
        return "bear"
    return "range"
