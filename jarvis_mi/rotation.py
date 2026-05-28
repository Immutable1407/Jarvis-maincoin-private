from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class RotationDecision:
    rotate: bool
    edge: float
    reason_codes: list[str]
    def to_dict(self) -> dict:
        return asdict(self)

def should_rotate(hold_score: float, candidate_score: float, friction_cost: float = 3.0, correlation_penalty: float = 5.0, threshold: float = 20.0) -> RotationDecision:
    edge = candidate_score - hold_score - friction_cost - correlation_penalty
    if edge > threshold:
        return RotationDecision(True, edge, ['candidate_materially_better'])
    return RotationDecision(False, edge, ['rotation_edge_too_small'])
