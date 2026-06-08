"""Hermes Mi v1.4.2 attribution schema and helpers.

Pure helpers for lifecycle and attribution keys. No trading behavior here —
this is the cold-path attribution layer.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any


# ── Key generators ──────────────────────────────────────────────────────────

def fill_key(row: dict) -> str:
    """Stable fill identity from tradeId/billId or composite fallback."""
    for key in ("tradeId", "billId"):
        val = row.get(key)
        if val:
            return f"{key}:{val}"
    return "cmp:" + "|".join(
        str(row.get(k, "")) for k in ("ordId", "instId", "fillTime", "fillPx", "fillSz", "side")
    )


def parse_okx_ts_to_bjt_day(row: dict) -> str | None:
    """Parse OKX fillTime/cTime into BJT (UTC+8) YYYY-MM-DD string.

    Handles numeric millisecond timestamps (int/float/string) and ISO-8601
    strings. Returns None when parsing fails.
    """
    raw = row.get("fillTime") or row.get("cTime") or row.get("ts") or row.get("timestamp") or row.get("time")
    if raw in (None, ""):
        return None
    try:
        if isinstance(raw, (int, float)) or str(raw).isdigit():
            val = float(raw)
            if val > 1e12:          # milliseconds
                val /= 1000.0
            return (
                datetime.fromtimestamp(val, timezone.utc)
                .astimezone(timezone(timedelta(hours=8)))
                .strftime("%Y-%m-%d")
            )
        # ISO-8601 with possible 'Z' suffix
        txt = str(raw).replace("Z", "+00:00")
        return (
            datetime.fromisoformat(txt)
            .astimezone(timezone(timedelta(hours=8)))
            .strftime("%Y-%m-%d")
        )
    except Exception:
        return None


def infer_fill_role(
    row: dict,
    matching_decision: dict | None = None,
    open_position_snapshot: dict | None = None,
) -> str:
    """Best-effort classification: 'entry', 'exit', or 'unknown'.

    Prefer explicit metadata and OKX `posSide` when available. For hedge-mode
    swaps, `side` alone is ambiguous: `sell` can be short entry or long exit;
    `buy` can be long entry or short exit. `posSide` resolves that ambiguity.
    """
    # Explicit exit markers
    if row.get("guardian_action") or row.get("exit_reason") or row.get("exit_rule"):
        return "exit"

    bill_type = str(row.get("billType") or row.get("type") or row.get("subType") or "").lower()
    exec_type = str(row.get("execType") or "").lower()
    if "close" in bill_type or "close" in exec_type:
        return "exit"

    fill_side = str(row.get("side") or "").lower()
    pos_side = str(row.get("posSide") or row.get("pos_side") or "").lower()
    fill_pnl = 0.0
    try:
        fill_pnl = float(row.get("fillPnl") or row.get("realizedPnl") or row.get("pnl") or 0.0)
    except Exception:
        fill_pnl = 0.0

    if pos_side == "long":
        if fill_side == "buy" and abs(fill_pnl) < 1e-12:
            return "entry"
        if fill_side == "sell":
            return "exit"
    elif pos_side == "short":
        if fill_side == "sell" and abs(fill_pnl) < 1e-12:
            return "entry"
        if fill_side == "buy":
            return "exit"

    # Decision-based inference
    if matching_decision:
        selected = matching_decision.get("selected") or {}
        dec_side = (selected.get("side") or matching_decision.get("side") or "").lower()
        # entry: buy for long signal, sell for short signal
        if dec_side == "long" and fill_side == "buy":
            return "entry"
        if dec_side == "short" and fill_side == "sell":
            return "entry"
        # exit: opposite side
        if dec_side == "long" and fill_side == "sell":
            return "exit"
        if dec_side == "short" and fill_side == "buy":
            return "exit"

    return "unknown"


def attribution_group_key(row: dict) -> str:
    """Stable attribution group key: instId + side + posSide + strategy_lane.

    Used to aggregate fills into meaningful lifecycle groups for PnL reporting.
    """
    inst_id = row.get("instId") or row.get("inst_id") or ""
    side = row.get("side") or ""
    pos_side = row.get("posSide") or ""
    lane = row.get("strategy_lane") or "unknown"
    return f"{inst_id}|{side}|{pos_side}|{lane}"


# ── Attribution summary ─────────────────────────────────────────────────────

def summarize_attribution(
    fills: list[dict],
    decisions: list[dict] | None = None,
    guardian: list[dict] | None = None,
    *,
    day: str | None = None,
) -> dict:
    """Report realized PnL by lane, near-miss status, symbol, side, and exit rule.

    Parameters
    ----------
    fills : list[dict]
        Enriched fill records (each should carry strategy_lane, near_miss_pass, etc.).
    decisions : list[dict] | None
        Decision ledger for near-miss / lane context.
    guardian : list[dict] | None
        Guardian ledger for exit-rule tagging.
    day : str | None
        Optional BJT YYYY-MM-DD filter.

    Returns
    -------
    dict with keys:
        by_lane, by_near_miss, by_symbol_side, by_exit_rule, unknown_attribution,
        total_realized_net, total_fees, total_fill_count
    """
    from collections import defaultdict
    from .performance import _dedupe_key, _float

    decisions = decisions or []
    guardian = guardian or []

    # Filter by day
    if day:
        fills = [f for f in fills if parse_okx_ts_to_bjt_day(f) == day]

    # Dedupe
    seen = set()
    deduped: list[dict] = []
    for f in fills:
        key = _dedupe_key(f)
        if key not in seen:
            seen.add(key)
            deduped.append(f)

    # Aggregation structures
    by_lane: dict[str, dict] = defaultdict(lambda: {
        "realized_net": 0.0, "fees": 0.0, "fill_count": 0,
        "win_count": 0, "loss_count": 0,
    })
    by_near_miss: dict[str, dict] = defaultdict(lambda: {
        "realized_net": 0.0, "fill_count": 0,
    })
    by_symbol_side: dict[str, dict] = defaultdict(lambda: {
        "realized_net": 0.0, "fill_count": 0,
    })
    by_exit_rule: dict[str, dict] = defaultdict(lambda: {
        "realized_net": 0.0, "fill_count": 0,
    })
    unknown_fills: list[str] = []

    for f in deduped:
        lane = f.get("strategy_lane") or "unknown"
        near_miss = f.get("near_miss_pass")
        inst_id = f.get("instId") or f.get("inst_id") or "?"
        side = f.get("side") or "?"
        exit_rule = f.get("exit_rule") or "unknown"
        pnl = _float(f, "pnl", "realizedPnl", "fillPnl")
        fee = _float(f, "fee")
        realized_net = pnl + fee

        # by_lane
        bl = by_lane[lane]
        bl["realized_net"] += realized_net
        bl["fees"] += fee
        bl["fill_count"] += 1
        if realized_net > 0:
            bl["win_count"] += 1
        elif realized_net < 0:
            bl["loss_count"] += 1

        # by_near_miss
        nm_key = "true" if near_miss else "false"
        by_near_miss[nm_key]["realized_net"] += realized_net
        by_near_miss[nm_key]["fill_count"] += 1

        # by_symbol_side
        ss_key = f"{inst_id}_{side}"
        by_symbol_side[ss_key]["realized_net"] += realized_net
        by_symbol_side[ss_key]["fill_count"] += 1

        # by_exit_rule
        by_exit_rule[exit_rule]["realized_net"] += realized_net
        by_exit_rule[exit_rule]["fill_count"] += 1

        # unknown attribution
        if lane == "unknown":
            unknown_fills.append(fill_key(f))
        if f.get("attribution_warning"):
            unknown_fills.append(f"{fill_key(f)}:{f.get('attribution_warning')}")

    # Compute lane avg_net_per_fill
    for lane, data in by_lane.items():
        if data["fill_count"] > 0:
            data["avg_net_per_fill"] = data["realized_net"] / data["fill_count"]
        else:
            data["avg_net_per_fill"] = 0.0

    total_realized_net = sum(d["realized_net"] for d in by_lane.values())
    total_fees = sum(d["fees"] for d in by_lane.values())

    return {
        "by_lane": {k: dict(v) for k, v in sorted(by_lane.items())},
        "by_near_miss": {k: dict(v) for k, v in sorted(by_near_miss.items())},
        "by_symbol_side": {k: dict(v) for k, v in sorted(by_symbol_side.items())},
        "by_exit_rule": {k: dict(v) for k, v in sorted(by_exit_rule.items())},
        "unknown_attribution": {
            "count": len(unknown_fills),
            "sample_keys": unknown_fills[:20],
        },
        "total_realized_net": total_realized_net,
        "total_fees": total_fees,
        "total_fill_count": len(deduped),
    }
