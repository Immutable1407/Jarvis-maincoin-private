from __future__ import annotations


def _position_direction(pos: dict) -> str:
    if pos.get("posSide") in {"long", "short"}:
        return str(pos.get("posSide"))
    return "long" if float(pos.get("pos") or 0) > 0 else "short"


def _float_field(pos: dict, *names: str) -> float | None:
    for name in names:
        raw = pos.get(name)
        if raw in (None, ""):
            continue
        try:
            val = abs(float(raw))
        except (TypeError, ValueError):
            continue
        if val > 0:
            return val
    return None


def position_margin_used(pos: dict) -> float:
    """Best-effort USDT margin use for an OKX position.

    Prefer explicit OKX margin fields. If absent, estimate from notional and
    leverage. If mark price is present but not notional, estimate from contract
    count; this is conservative enough for portfolio gating and testable without
    private runtime snapshots.
    """
    explicit = _float_field(pos, "imr", "margin", "marginSz", "posMargin", "initialMargin")
    if explicit is not None:
        return explicit

    notional = _float_field(pos, "notionalUsd", "notional", "usdNotional")
    if notional is None:
        pos_amt = _float_field(pos, "pos", "availPos")
        mark_px = _float_field(pos, "markPx", "last", "avgPx")
        ct_val = _float_field(pos, "ctVal") or 1.0
        if pos_amt is not None and mark_px is not None:
            notional = pos_amt * ct_val * mark_px
    lever = _float_field(pos, "lever", "leverage") or 1.0
    if notional is None:
        return 0.0
    return notional / max(1.0, lever)


def portfolio_margin_used(positions: list[dict]) -> float:
    return sum(position_margin_used(p) for p in positions)


def portfolio_allows_entry(
    positions: list[dict],
    signal,
    active_max_positions: int = 1,
    enable_second_position: bool = False,
    allow_mixed_direction_portfolio: bool = False,
) -> tuple[bool, list[str]]:
    reasons = []
    if len(positions) >= active_max_positions:
        return False, ["active_max_positions_reached"]
    if len(positions) >= 1 and not enable_second_position:
        return False, ["second_position_disabled"]
    same = [p for p in positions if p.get("instId") == getattr(signal, "inst_id", None)]
    if same:
        return False, ["same_symbol_position_exists"]
    dirs = [_position_direction(p) for p in positions]
    if dirs and getattr(signal, "side", None) not in dirs:
        if not allow_mixed_direction_portfolio:
            return False, ["mixed_direction_portfolio_blocked"]
        reasons.append("mixed_direction_portfolio")
    return True, reasons or ["portfolio_allows_entry"]


def portfolio_allows_sized_entry(
    positions: list[dict],
    signal,
    new_margin: float,
    equity: float,
    active_max_positions: int = 1,
    enable_second_position: bool = False,
    portfolio_margin_cap_pct: float = 0.60,
    single_position_margin_cap_pct: float = 0.35,
    second_position_margin_cap_pct: float = 0.30,
    allow_mixed_direction_portfolio: bool = False,
) -> tuple[bool, list[str]]:
    ok, reasons = portfolio_allows_entry(
        positions,
        signal,
        active_max_positions=active_max_positions,
        enable_second_position=enable_second_position,
        allow_mixed_direction_portfolio=allow_mixed_direction_portfolio,
    )
    if not ok:
        return ok, reasons

    if equity <= 0:
        return False, ["invalid_equity"]

    cap = equity * portfolio_margin_cap_pct
    current = portfolio_margin_used(positions)
    if new_margin > equity * single_position_margin_cap_pct:
        return False, ["single_position_margin_cap_exceeded"]
    if positions and new_margin > equity * second_position_margin_cap_pct:
        return False, ["second_position_margin_cap_exceeded"]
    if current + new_margin > cap:
        return False, ["portfolio_margin_cap_exceeded"]

    return True, reasons + ["portfolio_margin_guard_passed"]
