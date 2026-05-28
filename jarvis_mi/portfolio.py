from __future__ import annotations

def portfolio_allows_entry(positions: list[dict], signal, active_max_positions: int = 1, enable_second_position: bool = False) -> tuple[bool, list[str]]:
    reasons=[]
    if len(positions) >= active_max_positions:
        return False, ['active_max_positions_reached']
    if len(positions) >= 1 and not enable_second_position:
        return False, ['second_position_disabled']
    same = [p for p in positions if p.get('instId') == getattr(signal, 'inst_id', None)]
    if same:
        return False, ['same_symbol_position_exists']
    dirs = [('long' if (p.get('posSide') == 'long' or float(p.get('pos') or 0) > 0) else 'short') for p in positions]
    if dirs and getattr(signal, 'side', None) not in dirs:
        reasons.append('mixed_direction_portfolio')
    return True, reasons or ['portfolio_allows_entry']
