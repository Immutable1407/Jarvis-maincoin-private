# Hermes Mi v1.4.3 Release Notes

## Summary

`v1.4.3-stop-algo-schema-hotfix` is a live hot-path safety patch over v1.4.2. It fixes the OKX stop-loss algo payload used immediately after a market entry.

## Root cause

`OKXMiClient.place_stop_algo()` sent generic conditional fields:

- `triggerPx`
- `orderPx`
- `triggerPxType`

For OKX `/api/v5/trade/order-algo` stop-loss conditional orders, live OKX requires stop-loss-specific fields:

- `slTriggerPx`
- `slOrdPx`
- `slTriggerPxType`

The old payload produced OKX error `50015: Either parameter tpTriggerPx or slTriggerPx is required` after an entry order had already been submitted.

## Fix

- `jarvis_mi/okx_mi_client.py` now sends `slTriggerPx`, `slOrdPx=-1`, and `slTriggerPxType=last` for standalone reduce-only stop-loss algos.
- Added regression coverage in `tests/mi/test_execution.py` to assert the exact OKX stop-loss fields and reject legacy generic fields.
- Version metadata bumped to `v1.4.3-stop-algo-schema-hotfix` / `mi_v1_4_3_stop_algo_schema_hotfix`.

## What did NOT change

- No trading thresholds changed.
- No sizing, leverage, margin caps, lane scoring, guardian logic, allowed instruments, or account isolation changed.
- v1.4.2 attribution layer remains intact.

## Verification

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 -m pytest -q tests/mi/test_execution.py
python3 scripts/mi/mi_healthcheck.py
```
