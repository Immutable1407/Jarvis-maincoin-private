from __future__ import annotations
import time
from .account_guard import assert_allowed_inst, assert_mi_account
from .config_mi import MiConfig
from .indicators import fmt_step
from .ledger import append_jsonl, utc_now
from .okx_mi_client import OKXMiClient
from .sizing import compute_size, SizeDecision


def close_side_for(direction: str) -> str:
    return "sell" if direction == "long" else "buy"


def open_side_for(direction: str) -> str:
    return "buy" if direction == "long" else "sell"


def pos_side_for(direction: str) -> str:
    return "long" if direction == "long" else "short"


def format_price(px: float, tick_sz: str) -> str:
    return fmt_step(px, tick_sz)


def execute_entry(client: OKXMiClient, cfg: MiConfig, inst: dict, signal, equity: float, risk_decision=None) -> dict:
    assert_mi_account(client, cfg)
    assert_allowed_inst(signal.inst_id, cfg)
    direction = signal.side
    if direction not in {"long", "short"}:
        raise RuntimeError("execute_entry called without direction")
    leverage = int(getattr(risk_decision, "leverage", cfg.default_leverage) or cfg.default_leverage)
    margin_pct = float(getattr(risk_decision, "margin_pct", cfg.margin_pct) or cfg.margin_pct)
    max_loss_pct = float(getattr(risk_decision, "max_loss_pct", cfg.max_loss_pct) or cfg.max_loss_pct)
    size: SizeDecision = compute_size(
        equity=equity,
        price=signal.entry_ref,
        stop=signal.stop,
        ct_val=inst["ctVal"],
        lot_sz=inst["lotSz"],
        min_sz=inst["minSz"],
        leverage=leverage,
        margin_pct=margin_pct,
        max_loss_pct=max_loss_pct,
    )
    if size.margin > equity * cfg.max_margin_pct:
        raise RuntimeError(f"margin cap exceeded: {size.margin:.4f} > {equity * cfg.max_margin_pct:.4f}")
    if size.stop_loss_usdt > equity * max_loss_pct * 1.02:
        raise RuntimeError("risk cap exceeded after sizing")
    pos_side = pos_side_for(direction)
    client.set_leverage(signal.inst_id, leverage, pos_side=pos_side)
    clid = ("MI" + str(int(time.time())) + direction[0] + signal.inst_id.replace("-", ""))[:32]
    order = client.market_order(signal.inst_id, open_side_for(direction), size.sz, pos_side=pos_side, reduce_only=False, cl_ord_id=clid)
    # Place standalone reduce-only stop immediately; guardian also enforces local stop.
    stop_px = format_price(signal.stop, inst["tickSz"])
    stop = client.place_stop_algo(signal.inst_id, close_side_for(direction), size.sz, stop_px, pos_side=pos_side)
    rec = {
        "event": "ENTRY_SUBMITTED",
        "instId": signal.inst_id,
        "direction": direction,
        "leverage": leverage,
        "sz": size.sz,
        "entry_ref": signal.entry_ref,
        "stop_px": stop_px,
        "score": signal.score,
        "reason": signal.reason,
        "sizing": size.__dict__,
        "order": order.get("data"),
        "stop_algo": stop.get("data"),
        "strategy_tag": cfg.strategy_tag,
        "risk_decision": risk_decision.to_dict() if hasattr(risk_decision, "to_dict") else None,
    }
    append_jsonl("trades.jsonl", rec)
    return rec


def reduce_only_fraction(client: OKXMiClient, cfg: MiConfig, pos: dict, fraction: float, reason: str, lot_sz: str | None = None, min_sz: str | None = None) -> dict:
    assert_mi_account(client, cfg)
    inst_id = pos.get("instId")
    assert_allowed_inst(inst_id, cfg)
    pos_amt = abs(float(pos.get("pos") or 0))
    if pos_amt <= 0:
        return {"skipped": "zero_position"}
    direction = str(pos.get("posSide")) if pos.get("posSide") in {"long", "short"} else ("long" if float(pos.get("pos") or 0) > 0 else "short")
    side = close_side_for(direction)
    qty = pos_amt * max(0.0, min(1.0, fraction))
    if lot_sz:
        sz = fmt_step(qty, lot_sz)
    else:
        sz = str(qty)
    if float(sz) <= 0 or (min_sz is not None and float(sz) < float(min_sz)):
        rec = {"event": "REDUCE_ONLY_PARTIAL_SKIPPED", "reason": reason, "instId": inst_id, "direction": direction, "fraction": fraction, "raw_qty": qty, "sz": sz, "minSz": min_sz, "strategy_tag": cfg.strategy_tag}
        append_jsonl("trades.jsonl", rec)
        return rec
    res = client.market_order(inst_id, side, sz, pos_side=pos_side_for(direction), reduce_only=True)
    rec = {"event": "REDUCE_ONLY_PARTIAL", "reason": reason, "instId": inst_id, "direction": direction, "fraction": fraction, "sz": sz, "order": res.get("data"), "strategy_tag": cfg.strategy_tag}
    append_jsonl("trades.jsonl", rec)
    return rec


def reduce_only_close(client: OKXMiClient, cfg: MiConfig, pos: dict, reason: str) -> dict:
    return reduce_only_fraction(client, cfg, pos, 1.0, reason)
