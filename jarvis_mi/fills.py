from __future__ import annotations
import json
from pathlib import Path
from .config_mi import STATE_DIR
from .ledger import append_jsonl
from .attribution import infer_fill_role, attribution_group_key

SEEN_FILLS_PATH = STATE_DIR / "fill_sync_seen.json"


def _decision_order_ids(decision: dict) -> tuple[set[str], set[str]]:
    """Extract ordId/clOrdId from both selected fields and nested trade response."""
    ord_ids: set[str] = set()
    cl_ord_ids: set[str] = set()
    selected = decision.get("selected") or {}
    for src in (selected, decision):
        if src.get("ordId"):
            ord_ids.add(str(src.get("ordId")))
        if src.get("clOrdId"):
            cl_ord_ids.add(str(src.get("clOrdId")))
    trade = decision.get("trade") or {}
    for item in trade.get("order") or []:
        if isinstance(item, dict):
            if item.get("ordId"):
                ord_ids.add(str(item.get("ordId")))
            if item.get("clOrdId"):
                cl_ord_ids.add(str(item.get("clOrdId")))
    return ord_ids, cl_ord_ids


def _decision_inst_side(decision: dict) -> tuple[str | None, str | None]:
    selected = decision.get("selected") or {}
    return selected.get("inst_id") or selected.get("instId") or decision.get("instId"), selected.get("side") or decision.get("side")


def _fill_key(row: dict) -> str:
    for key in ("tradeId", "billId"):
        val = row.get(key)
        if val:
            return f"{key}:{val}"
    return "cmp:" + "|".join(str(row.get(k, "")) for k in ("ordId", "instId", "fillTime", "fillPx", "fillSz", "side"))


def _load_seen() -> dict[str, float]:
    """Load seen fill keys with first-seen ordering metadata.

    Backwards compatible with the original v1.3.0 list/keys state. New state
    stores `seen_at` so the 5000-key cap trims oldest keys, not lexicographic
    keys that may have nothing to do with recency.
    """
    try:
        raw = json.loads(SEEN_FILLS_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return {str(k): float(i) for i, k in enumerate(raw)}
        keys = raw.get("keys", []) if isinstance(raw, dict) else []
        seen_at = raw.get("seen_at", {}) if isinstance(raw, dict) else {}
        return {str(k): float(seen_at.get(str(k), i)) for i, k in enumerate(keys)}
    except Exception:
        return {}


def _save_seen(seen: dict[str, float], max_keys: int = 5000) -> None:
    SEEN_FILLS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(seen.items(), key=lambda kv: kv[1])[-max_keys:]
    keys = [k for k, _ in ordered]
    seen_at = {k: seen[k] for k in keys}
    SEEN_FILLS_PATH.write_text(json.dumps({"keys": keys, "seen_at": seen_at}, ensure_ascii=False), encoding="utf-8")


def enrich_fill_with_decision_attribution(row: dict, decisions: list[dict]) -> dict:
    """Copy v1.4.2 lane/profit attribution from the latest matching decision.

    Fills are exchange-ledger events; this best-effort enrichment is report-only
    and does not affect execution or dedupe keys.

    Matching strategy:
    1. Exact clOrdId/ordId match (when fill carries the order ID)
    2. Fall back to latest matching instId + side decision
    3. If no match → fill_role="unknown", attribution_warning="no_matching_decision"
    """
    out = dict(row)
    inst_id = out.get("instId") or out.get("inst_id")
    fill_side = str(out.get("side") or "").lower()
    fill_pos_side = str(out.get("posSide") or out.get("pos_side") or "").lower()
    fill_ord_id = str(out.get("ordId") or "")
    fill_cl_ord_id = str(out.get("clOrdId") or "")

    # In OKX hedge-mode fills, posSide is the safest direction key. Fallback
    # to fill side only when posSide is absent (old/synthetic records).
    wanted_signal_side = fill_pos_side if fill_pos_side in {"long", "short"} else ("short" if fill_side == "sell" else "long" if fill_side == "buy" else None)
    match = None

    # Prefer exact clOrdId/ordId match
    for decision in reversed(decisions or []):
        dec_ord_ids, dec_cl_ord_ids = _decision_order_ids(decision)
        if fill_cl_ord_id and fill_cl_ord_id in dec_cl_ord_ids:
            match = decision
            break
        if fill_ord_id and fill_ord_id in dec_ord_ids:
            match = decision
            break

    # Fall back to latest instId + signal side / posSide
    if not match:
        for decision in reversed(decisions or []):
            dec_inst, dec_side = _decision_inst_side(decision)
            if dec_inst != inst_id:
                continue
            if wanted_signal_side and dec_side not in {wanted_signal_side, None}:
                continue
            match = decision
            break

    if not match:
        out["strategy_lane"] = "unknown"
        out["fill_role"] = "unknown"
        out["attribution_warning"] = "no_matching_decision"
        out["attribution_group_key"] = attribution_group_key(out)
        return out

    selected = match.get("selected") or {}
    preview = match.get("profit_preview") or {}
    risk = match.get("risk_decision") or {}

    # ── Strategy identity ──
    lane = selected.get("strategy_lane") or preview.get("strategy_lane") or preview.get("lane")
    out["strategy_lane"] = lane or "unknown"

    tag = out.get("strategy_tag") or match.get("strategy_tag")
    if tag:
        out["strategy_tag"] = tag

    # ── Near-miss and expected profit ──
    out["near_miss_pass"] = bool(preview.get("near_miss_pass") or False)
    for key in ("expected_net_pct", "expected_tp1_net_pct"):
        val = preview.get(key)
        if val is None and key == "expected_net_pct":
            val = preview.get("expected_trade_net_pct")
        if val is not None:
            out[key] = val

    # ── Score ──
    score = selected.get("score") or selected.get("total_score")
    if score is not None:
        out["score"] = float(score)

    # ── Context fields ──
    for ctx_key in ("market_regime", "resonance_adjustment", "portfolio_position_count",
                     "is_second_position", "same_direction_group"):
        val = selected.get(ctx_key) or match.get(ctx_key) or preview.get(ctx_key)
        if val is not None:
            out[ctx_key] = val

    # ── Fill role ──
    out["fill_role"] = infer_fill_role(out, match)

    # ── Attribution group key ──
    out["attribution_group_key"] = attribution_group_key(out)

    return out


def sync_fills(client, cfg, limit: int = 100) -> dict:
    # OKX fills history is account-private; keep tolerant so the cron never blocks guardians.
    data = client.request('GET', '/api/v5/trade/fills-history', {'instType': 'SWAP', 'limit': str(limit)}).get('data') or []
    mi = [x for x in data if str(x.get('clOrdId','')).startswith('MI') or x.get('instId') in cfg.allowed_insts]
    seen = _load_seen()
    try:
        from .performance import _read_jsonl
        decisions = _read_jsonl("decisions.jsonl")
        # Trades ledger contains the actual OKX ordId/clOrdId returned by entry
        # submission; include it as report-only attribution context.
        trade_context = [
            {"event": "TRADE_CONTEXT", "selected": {"inst_id": t.get("instId"), "side": t.get("direction"),
                                                       "strategy_lane": t.get("strategy_lane"), "score": t.get("score")},
             "strategy_tag": t.get("strategy_tag"),
             "profit_preview": {"near_miss_pass": t.get("near_miss_pass"),
                                "expected_net_pct": t.get("expected_net_pct"),
                                "expected_tp1_net_pct": t.get("expected_tp1_net_pct")},
             "trade": {"order": t.get("order") or []}}
            for t in _read_jsonl("trades.jsonl")
            if t.get("event") == "ENTRY_SUBMITTED"
        ]
        decisions = decisions + trade_context
    except Exception:
        decisions = []
    new = 0
    skipped = 0
    for row in reversed(mi):
        key = _fill_key(row)
        if key in seen:
            skipped += 1
            continue
        seen[key] = float(len(seen) + new + 1)
        enriched = enrich_fill_with_decision_attribution(row, decisions)
        append_jsonl('fills.jsonl', {'event': 'FILL_SYNC', 'fill_sync_key': key, **enriched})
        new += 1
    _save_seen(seen)
    return {'event': 'FILL_SYNC', 'count': len(mi), 'new': new, 'skipped_duplicates': skipped}
