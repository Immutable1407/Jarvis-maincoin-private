from __future__ import annotations
from .ledger import append_jsonl

def sync_fills(client, cfg, limit: int = 100) -> dict:
    # OKX fills history is account-private; keep tolerant so the cron never blocks guardians.
    data = client.request('GET', '/api/v5/trade/fills-history', {'instType': 'SWAP', 'limit': str(limit)}).get('data') or []
    mi = [x for x in data if str(x.get('clOrdId','')).startswith('MI') or x.get('instId') in cfg.allowed_insts]
    for row in reversed(mi):
        append_jsonl('fills.jsonl', {'event': 'FILL_SYNC', **row})
    return {'event': 'FILL_SYNC', 'count': len(mi)}
