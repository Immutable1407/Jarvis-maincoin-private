from __future__ import annotations
from dataclasses import dataclass
from .indicators import fmt_step


@dataclass
class SizeDecision:
    sz: str
    notional: float
    margin: float
    max_loss: float
    stop_loss_usdt: float
    reason: list[str]


def compute_size(equity: float, price: float, stop: float, ct_val: str, lot_sz: str, min_sz: str, leverage: int, margin_pct: float, max_loss_pct: float) -> SizeDecision:
    reasons: list[str] = []
    margin = equity * margin_pct
    notional = margin * leverage
    stop_pct = abs(price - stop) / price if price else 0
    max_loss = equity * max_loss_pct
    stop_loss = notional * stop_pct
    if stop_loss > max_loss and stop_pct > 0:
        notional = max_loss / stop_pct
        margin = notional / leverage
        stop_loss = max_loss
        reasons.append("risk_cap_reduced_notional")
    raw_sz = notional / (float(ct_val) * price)
    sz_s = fmt_step(raw_sz, lot_sz)
    if float(sz_s) < float(min_sz):
        sz_s = fmt_step(float(min_sz), lot_sz)
        notional = float(sz_s) * float(ct_val) * price
        margin = notional / leverage
        stop_loss = notional * stop_pct
        reasons.append("raised_to_min_sz")
    return SizeDecision(sz_s, notional, margin, max_loss, stop_loss, reasons)
