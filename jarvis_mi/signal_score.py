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
    strategy_lane: str = "none"   # trend_confirmed | trend_probe | range_swing | none
    tp1_r: float = 1.2
    tp1_fraction: float = 0.5


def _risk_pct(price: float, stop: float) -> float:
    return abs(price - stop) / price if price else 0.0


def _base_signal(inst_id: str, h1: list[dict[str, float]], m15: list[dict[str, float]]) -> Signal:
    price = m15[-1]["c"] if m15 else 0.0
    return Signal(inst_id, None, 0.0, ["no_v1_2_trigger"], price, 0.0, 0.0)


def _range_swing_signal(
    inst_id: str,
    h1: list[dict[str, float]],
    m15: list[dict[str, float]],
    btc_bias: str | None,
) -> Signal | None:
    """v1.2.0 range lane: BTC/maincoins spend much time chopping.

    Trade only near an established 15m range edge with a short time horizon. This is
    still pure-code and conservative; it is not a blind mean-reversion catch.
    """
    closes = [x["c"] for x in m15]
    price = closes[-1]
    recent = m15[-48:]
    hi = max(x["h"] for x in recent)
    lo = min(x["l"] for x in recent)
    width = (hi - lo) / price if price else 0.0
    if width < 0.006 or width > 0.045:
        return None
    a15 = atr(m15, 14)[-1]
    lower_zone = lo + (hi - lo) * 0.22
    upper_zone = hi - (hi - lo) * 0.22
    prev = m15[-2]
    side = None
    stop = 0.0
    reasons: list[str] = ["lane_range_swing", f"range_width_{width:.3f}"]
    if price <= lower_zone and price > prev["c"] and btc_bias != "bear":
        side = "long"
        stop = min(lo, price - 1.1 * a15)
        reasons.append("range_lower_reclaim")
    elif price >= upper_zone and price < prev["c"] and btc_bias != "bull":
        side = "short"
        stop = max(hi, price + 1.1 * a15)
        reasons.append("range_upper_reject")
    if not side or stop <= 0:
        return None
    risk = _risk_pct(price, stop)
    score = 66.0
    if 0.004 <= risk <= 0.018:
        score += 4
        reasons.append("range_stop_usable")
    if btc_bias == "range":
        score += 3
        reasons.append("btc_range_aligned")
    return Signal(inst_id, side, score, reasons, price, stop, 1.8, "range_swing", 1.0, 0.7)


def evaluate_inst(inst_id: str, h1: list[dict[str, float]], m15: list[dict[str, float]], btc_bias: str | None, cfg=None) -> Signal:
    if len(h1) < 60 or len(m15) < 80:
        return Signal(inst_id, None, 0, ["insufficient_candles"], 0, 0, 0)
    h1c = [x["c"] for x in h1]
    m15c = [x["c"] for x in m15]
    e20 = ema(h1c, 20)
    e50 = ema(h1c, 50)
    m_e20 = ema(m15c, 20)
    m_e50 = ema(m15c, 50)
    a15 = atr(m15, 14)
    last = h1[-1]
    mlast = m15[-1]
    price = mlast["c"]
    atrv = a15[-1]
    recent_high = max(x["h"] for x in m15[-8:-1])
    recent_low = min(x["l"] for x in m15[-8:-1])
    side = None
    lane = "none"
    reasons: list[str] = []
    score = 0.0
    stop = 0.0
    expected_r = 0.0
    tp1_r = 1.2
    tp1_fraction = 0.5

    h1_bull = last["c"] > e20[-1] > e50[-1] and e20[-1] > e20[-4]
    h1_bear = last["c"] < e20[-1] < e50[-1] and e20[-1] < e20[-4]
    h1_bull_forming = last["c"] > e20[-1] and e20[-1] >= e20[-4] and last["c"] >= e50[-1] * 0.995
    h1_bear_forming = last["c"] < e20[-1] and e20[-1] <= e20[-4] and last["c"] <= e50[-1] * 1.005
    m_break_long = price > m_e20[-1] and (price > recent_high or (m15[-2]["c"] < m_e20[-2] and price > m_e20[-1]))
    m_break_short = price < m_e20[-1] and (price < recent_low or (m15[-2]["c"] > m_e20[-2] and price < m_e20[-1]))
    m_pullback_long = price > m_e20[-1] and m15[-2]["l"] <= m_e20[-2] and price >= m_e50[-1] * 0.995
    m_pullback_short = price < m_e20[-1] and m15[-2]["h"] >= m_e20[-2] and price <= m_e50[-1] * 1.005

    if h1_bull and m_break_long:
        side = "long"
        lane = "trend_confirmed"
        score = 74
        reasons += ["lane_trend_confirmed", "observe_trend_strength", "setup_h1_bull", "trigger_m15_long"]
        stop = min(recent_low, price - 1.2 * atrv)
        expected_r = 1.5
        tp1_r = 1.2
        tp1_fraction = 0.5
    elif h1_bear and m_break_short:
        side = "short"
        lane = "trend_confirmed"
        score = 74
        reasons += ["lane_trend_confirmed", "observe_trend_weakness", "setup_h1_bear", "trigger_m15_short"]
        stop = max(recent_high, price + 1.2 * atrv)
        expected_r = 1.5
        tp1_r = 1.2
        tp1_fraction = 0.5
    elif h1_bull_forming and m_pullback_long and btc_bias != "bear":
        side = "long"
        lane = "trend_probe"
        score = 67
        reasons += ["lane_trend_probe", "setup_h1_bull_forming", "trigger_m15_pullback_reclaim"]
        stop = min(recent_low, price - 1.0 * atrv)
        expected_r = 1.8
        tp1_r = 1.0
        tp1_fraction = 0.7
    elif h1_bear_forming and m_pullback_short and btc_bias != "bull":
        side = "short"
        lane = "trend_probe"
        score = 67
        reasons += ["lane_trend_probe", "setup_h1_bear_forming", "trigger_m15_pullback_reject"]
        stop = max(recent_high, price + 1.0 * atrv)
        expected_r = 1.8
        tp1_r = 1.0
        tp1_fraction = 0.7
    else:
        range_sig = _range_swing_signal(inst_id, h1, m15, btc_bias) if getattr(cfg, "enable_three_lane_signals", True) else None
        if range_sig:
            return range_sig if range_sig.score >= 65 else _base_signal(inst_id, h1, m15)
        reasons.append("no_v1_2_trigger")

    if side:
        risk = _risk_pct(price, stop)
        if risk < 0.0015:
            score -= 10
            reasons.append("stop_too_tight")
        if risk > 0.025:
            score -= 15
            reasons.append("stop_too_wide")
        if btc_bias == "bear" and side == "long" and inst_id != "BTC-USDT-SWAP":
            score -= 20
            reasons.append("btc_against")
        if btc_bias == "bull" and side == "short" and inst_id != "BTC-USDT-SWAP":
            score -= 20
            reasons.append("btc_against")
        if (btc_bias == "bull" and side == "long") or (btc_bias == "bear" and side == "short"):
            score += 5
            reasons.append("btc_aligned")
    else:
        expected_r = 0
    return Signal(inst_id, side if score >= 65 else None, score, reasons, price, stop, expected_r, lane, tp1_r, tp1_fraction)


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
