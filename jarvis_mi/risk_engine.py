from __future__ import annotations
from dataclasses import dataclass, asdict
from .market_state import MarketState


@dataclass(frozen=True)
class RiskDecision:
    leverage: int
    margin_pct: float
    max_loss_pct: float
    risk_mode: str
    reason_codes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def decide_risk(
    market_state: MarketState,
    signal_score: float,
    volatility_pct: float,
    equity: float,
    recent_stopouts: int = 0,
    resonance_risk_multiplier: float = 1.0,
    strategy_lane: str = "trend_confirmed",
) -> RiskDecision:
    """Return v1.1.0 sizing risk for the next maincoin entry.

    v1.1.0 intentionally moves from low-margin/high-leverage to higher-margin,
    moderate-leverage exposure. The portfolio cap is enforced separately in
    ``portfolio_allows_sized_entry`` / ``execute_entry``.
    """
    reasons = list(market_state.reason_codes)
    if market_state.risk_budget == "zero" or market_state.direction_bias == "no_trade":
        return RiskDecision(0, 0.0, 0.0, "paused", reasons + ["market_state_paused"])

    if recent_stopouts >= 3:
        return RiskDecision(3, 0.05, 0.004, "probe", reasons + ["recent_stopouts_probe"])

    if strategy_lane == "range_swing":
        lev, margin, loss, mode = 6, 0.16, 0.012, "range"
    elif strategy_lane == "trend_probe":
        lev, margin, loss, mode = 8, 0.14, 0.014, "probe"
    elif market_state.risk_budget == "probe" or signal_score < 70:
        lev, margin, loss, mode = 5, 0.08, 0.008, "probe"
    elif market_state.btc_regime == "chop":
        lev, margin, loss, mode = 6, 0.14, 0.012, "reduced"
    elif market_state.risk_budget == "half":
        lev, margin, loss, mode = 8, 0.18, 0.018, "reduced"
    elif signal_score >= 90 and market_state.risk_budget == "full":
        lev, margin, loss, mode = 12, 0.32, 0.035, "strong"
    else:
        lev, margin, loss, mode = 10, 0.25, 0.03, "normal"

    if volatility_pct > 0.035:
        lev = min(lev, 8)
        margin *= 0.6
        loss *= 0.6
        reasons.append("high_vol_reduced")

    # Resonance can reduce risk, but does not raise v1.1.0 above hard caps.
    multiplier = max(0.0, min(1.0, resonance_risk_multiplier))
    margin *= multiplier
    loss *= multiplier

    return RiskDecision(int(lev), round(margin, 4), round(loss, 4), mode, reasons + [f"lane_{strategy_lane}"])
