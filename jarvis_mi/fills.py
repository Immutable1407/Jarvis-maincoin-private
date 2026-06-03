from __future__ import annotations
import json
from pathlib import Path
from .config_mi import STATE_DIR
from .ledger import append_jsonl

SEEN_FILLS_PATH = STATE_DIR / "fill_sync_seen.json"


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
    """Copy v1.4 lane/profit attribution from the latest matching decision.

    Fills are exchange-ledger events; this best-effort enrichment is report-only
    and does not affect execution or dedupe keys.
    """
    out = dict(row)
    inst_id = out.get("instId")
    fill_side = str(out.get("side") or "").lower()
    wanted_signal_side = "short" if fill_side == "sell" else "long" if fill_side == "buy" else None
    match = None
    for decision in reversed(decisions or []):
        selected = decision.get("selected") or {}
        if selected.get("inst_id") != inst_id and selected.get("instId") != inst_id:
            continue
        if wanted_signal_side and selected.get("side") not in {wanted_signal_side, None}:
            continue
        match = decision
        break
    if not match:
        return out
    selected = match.get("selected") or {}
    preview = match.get("profit_preview") or {}
    lane = selected.get("strategy_lane") or preview.get("strategy_lane") or preview.get("lane")
    if lane is not None:
        out["strategy_lane"] = lane
    for key in ("near_miss_pass", "expected_net_pct", "expected_tp1_net_pct"):
        val = preview.get(key)
        if val is None and key == "expected_net_pct":
            val = preview.get("expected_trade_net_pct")
        if val is not None:
            out[key] = val
    return out


def sync_fills(client, cfg, limit: int = 100) -> dict:
    # OKX fills history is account-private; keep tolerant so the cron never blocks guardians.
    data = client.request('GET', '/api/v5/trade/fills-history', {'instType': 'SWAP', 'limit': str(limit)}).get('data') or []
    mi = [x for x in data if str(x.get('clOrdId','')).startswith('MI') or x.get('instId') in cfg.allowed_insts]
    seen = _load_seen()
    try:
        from .performance import _read_jsonl
        decisions = _read_jsonl("decisions.jsonl")
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
