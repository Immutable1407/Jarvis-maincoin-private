from __future__ import annotations
from dataclasses import dataclass, asdict
from .indicators import ema, atr

@dataclass(frozen=True)
class MarketState:
    btc_regime: str
    maincoin_regime: str
    direction_bias: str
    frequency_mode: str
    risk_budget: str
    reason_codes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)

def _ret(candles: list[dict[str, float]], n: int = 12) -> float:
    if len(candles) <= n or candles[-n-1]['c'] == 0:
        return 0.0
    return candles[-1]['c'] / candles[-n-1]['c'] - 1.0

def _trend(candles: list[dict[str, float]]) -> str:
    if len(candles) < 60:
        return 'unknown'
    c = [x['c'] for x in candles]
    e20, e50 = ema(c, 20), ema(c, 50)
    last = c[-1]
    if last > e20[-1] > e50[-1] and e20[-1] >= e20[-4]:
        return 'up'
    if last < e20[-1] < e50[-1] and e20[-1] <= e20[-4]:
        return 'down'
    return 'flat'

def _volatility(candles: list[dict[str, float]]) -> float:
    if len(candles) < 20 or candles[-1]['c'] == 0:
        return 0.0
    return atr(candles, 14)[-1] / candles[-1]['c']

def classify_market_state(
    btc_h1: list[dict[str, float]],
    eth_h1: list[dict[str, float]] | None = None,
    sol_h1: list[dict[str, float]] | None = None,
    bnb_h1: list[dict[str, float]] | None = None,
) -> MarketState:
    reasons: list[str] = []
    btc_trend = _trend(btc_h1)
    btc_ret = _ret(btc_h1, 12)
    btc_vol = _volatility(btc_h1)
    alt_sets = [x for x in [eth_h1, sol_h1, bnb_h1] if x]
    alt_rets = [_ret(x, 12) for x in alt_sets] or [0.0]
    alt_up = sum(1 for r in alt_rets if r > 0.005)
    alt_down = sum(1 for r in alt_rets if r < -0.005)

    if btc_ret <= -0.035 or (btc_h1 and btc_h1[-1]['c'] <= btc_h1[0]['c'] * 0.75) or (btc_trend == 'down' and btc_vol >= 0.025):
        return MarketState('crash', 'decay', 'no_trade', 'pause', 'zero', ['btc_crash_or_high_vol_down'])
    if btc_trend == 'up' and btc_ret > 0.004:
        btc_regime = 'risk_on'; reasons.append('btc_uptrend')
    elif btc_trend == 'down' and btc_ret < -0.004:
        btc_regime = 'risk_off'; reasons.append('btc_downtrend')
    elif btc_vol >= 0.03:
        btc_regime = 'squeeze'; reasons.append('btc_high_vol_squeeze')
    else:
        btc_regime = 'chop'; reasons.append('btc_flat_or_mixed')

    if alt_up >= 2:
        main = 'expansion'; reasons.append('maincoins_broad_strength')
    elif alt_down >= 2:
        main = 'decay'; reasons.append('maincoins_broad_weakness')
    elif alt_up or alt_down:
        main = 'selective'; reasons.append('maincoins_selective')
    else:
        main = 'no_trade' if btc_regime in {'chop','squeeze'} else 'selective'

    if btc_regime == 'risk_on' and main in {'expansion','selective'}:
        return MarketState(btc_regime, main, 'long_only', 'normal', 'full' if main == 'expansion' else 'half', reasons)
    if btc_regime == 'risk_off' and main in {'decay','selective'}:
        return MarketState(btc_regime, main, 'short_only', 'normal', 'half', reasons)
    if btc_regime == 'squeeze':
        return MarketState(btc_regime, main, 'both', 'fast', 'probe', reasons)
    return MarketState(btc_regime, main, 'both', 'slow', 'half', reasons)
