from __future__ import annotations
from .ledger import append_jsonl

def record_proposal(proposal: dict) -> None:
    append_jsonl('proposals.jsonl', {'event': 'PARAM_PROPOSAL', **proposal})
