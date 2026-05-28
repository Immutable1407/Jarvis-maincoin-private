from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Resonance:
    mode: str
    score_adjustment: float
    risk_multiplier: float
    reason_codes: list[str]
    returns: dict[str, float]
    def to_dict(self) -> dict:
        return asdict(self)

def _ret(cs: list[dict[str, float]], n: int = 12) -> float:
    if not cs:
        return 0.0
    idx = max(0, len(cs)-1-n)
    base = cs[idx]['c']
    return cs[-1]['c']/base - 1.0 if base else 0.0

def compute_resonance(candles_by_inst: dict[str, list[dict[str, float]]]) -> Resonance:
    rets = {k: _ret(v) for k, v in candles_by_inst.items()}
    btc = rets.get('BTC-USDT-SWAP', 0.0)
    alts = {k:v for k,v in rets.items() if k != 'BTC-USDT-SWAP'}
    alt_up = sum(1 for v in alts.values() if v > 0.005)
    alt_down = sum(1 for v in alts.values() if v < -0.005)
    reasons=[]
    if btc > 0.003 and alt_up >= 2:
        return Resonance('aligned_long', 8.0, 1.0, ['btc_and_maincoins_aligned_long'], rets)
    if btc < -0.003 and alt_down >= 2:
        return Resonance('aligned_short', 8.0, 0.9, ['btc_and_maincoins_aligned_short'], rets)
    if btc < -0.003 and alt_up >= 2:
        reasons.append('btc_alt_divergence')
        return Resonance('divergent_alt_strength', -6.0, 0.6, reasons, rets)
    if btc > 0.003 and alt_down >= 2:
        reasons.append('btc_alt_divergence')
        return Resonance('divergent_alt_weakness', -6.0, 0.7, reasons, rets)
    return Resonance('mixed', 0.0, 0.75, ['mixed_maincoin_resonance'], rets)
