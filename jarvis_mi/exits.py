from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class ExitAction:
    kind: str
    fraction: float
    trigger_price: float | None
    reason: str
    def to_dict(self) -> dict:
        return asdict(self)

def _direction(pos: dict) -> str:
    if pos.get('posSide') in {'long', 'short'}:
        return str(pos.get('posSide'))
    return 'long' if float(pos.get('pos') or 0) > 0 else 'short'

def _r_multiple(direction: str, entry: float, initial_stop: float, mark: float) -> float:
    risk = abs(entry - initial_stop)
    if risk <= 0:
        return 0.0
    return (mark - entry) / risk if direction == 'long' else (entry - mark) / risk

def plan_exit_actions(pos: dict, entry: float, initial_stop: float, mark: float, state: dict, min_size: float = 0.0) -> list[ExitAction]:
    direction = _direction(pos)
    r = _r_multiple(direction, entry, initial_stop, mark)
    qty = abs(float(pos.get('pos') or 0))
    out: list[ExitAction] = []
    if r >= 0.8 and not state.get('breakeven_done'):
        out.append(ExitAction('move_stop_breakeven', 0.0, entry, f'mfe_{r:.2f}R_breakeven'))
    if r >= 1.2 and not state.get('partial_tp_1') and qty * 0.30 >= min_size:
        out.append(ExitAction('partial_tp_1', 0.30, None, f'mfe_{r:.2f}R_first_tp'))
    if r >= 2.0 and not state.get('partial_tp_2') and qty * 0.30 >= min_size:
        out.append(ExitAction('partial_tp_2', 0.30, None, f'mfe_{r:.2f}R_second_tp'))
    if r >= 1.5 and (state.get('partial_tp_1') or state.get('partial_tp_2')):
        trail = mark - abs(entry-initial_stop)*0.8 if direction == 'long' else mark + abs(entry-initial_stop)*0.8
        out.append(ExitAction('trailing_stop', 0.0, trail, f'mfe_{r:.2f}R_trailing'))
    return out
