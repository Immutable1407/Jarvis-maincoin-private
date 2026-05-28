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

def decide_risk(market_state: MarketState, signal_score: float, volatility_pct: float, equity: float, recent_stopouts: int = 0, resonance_risk_multiplier: float = 1.0) -> RiskDecision:
    reasons=list(market_state.reason_codes)
    if market_state.risk_budget == 'zero' or market_state.direction_bias == 'no_trade':
        return RiskDecision(0, 0.0, 0.0, 'paused', reasons + ['market_state_paused'])
    if recent_stopouts >= 3:
        return RiskDecision(3, 0.015, 0.003, 'probe', reasons + ['recent_stopouts_probe'])
    if market_state.risk_budget == 'probe' or signal_score < 70:
        lev, margin, loss, mode = 5, 0.02, 0.004, 'probe'
    elif market_state.btc_regime == 'chop':
        lev, margin, loss, mode = 10, 0.035, 0.007, 'reduced'
    elif market_state.risk_budget == 'half':
        lev, margin, loss, mode = 12, 0.04, 0.008, 'reduced'
    else:
        lev, margin, loss, mode = 20, 0.06, 0.012, 'normal'
    if volatility_pct > 0.035:
        lev = min(lev, 8); margin *= 0.6; loss *= 0.6; reasons.append('high_vol_reduced')
    margin *= max(0.0, min(1.0, resonance_risk_multiplier))
    loss *= max(0.0, min(1.0, resonance_risk_multiplier))
    return RiskDecision(int(lev), round(margin, 4), round(loss, 4), mode, reasons)
