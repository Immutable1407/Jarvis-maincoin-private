# Hermes Mi v1.4.1 — Entry / Report Fail-Loud Hotfix

Date: 2026-06-03

## Summary

v1.4.1 is a patch over v1.4.0 lane attribution + correlated short governor. It does **not** change the maincoin strategy’s risk caps, instruments, lane thresholds, max positions, or correlation governor. It fixes entry-path fail-loud behavior and daily-report PnL semantics.

## Fixes

1. **Entry order response validation**
   - `execute_entry()` now checks OKX set-leverage and market-order responses.
   - A market order that returns non-zero code fails closed.
   - A success response without `ordId` now raises `entry_order_missing_ordid` before attempting a standalone stop.

2. **Stop placement response validation**
   - Standalone stop algo response is now checked.
   - If the stop fails after entry, the system raises a loud error containing the entry order id, so the local guardian/health path can catch the unprotected position rather than silently recording a normal entry.

3. **Daily report PnL semantics**
   - Daily brief now reports **today’s** BJT deduped realized net after fees separately from all-time cumulative realized net.
   - This fixes the stale wording where a daily report could show cumulative fill PnL as if it were day-only PnL.

## Verification

```bash
cd /root/jarvis-mi
PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q jarvis_mi scripts/mi tests/mi
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests/mi
PYTHONDONTWRITEBYTECODE=1 python3 scripts/mi/mi_healthcheck.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/mi/mi_sync_fills.py
```

Result: all tests passed; healthcheck passed; fill sync was read-only and found no new fills.

## Trading impact

No aggression change. The patch only makes live entry attribution/stop-protection failures fail loud and makes human-facing PnL reporting more precise.
