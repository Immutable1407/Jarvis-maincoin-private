# Hermes Mi v2.0.1 — Entry Stop Observability + Close Quantization Patch

Date: 2026-06-13

## Scope

Patch release over v2.0.0 regime-adaptive maincoin foundation. No strategy-threshold, leverage, position-count, or risk-budget increase.

## Fixes

1. **Entry accepted before stop algo failure is now auditable**
   - After OKX accepts a market entry order and returns `ordId`, Mi immediately writes `ENTRY_ORDER_ACCEPTED_PENDING_STOP`.
   - If the standalone stop algo fails after the entry order, Mi writes `CRITICAL_ENTRY_STOP_FAILED_AFTER_ORDER` with order/stop context before raising.
   - This prevents a real position from becoming invisible to ledgers and postmortems when entry succeeds but stop placement fails.

2. **Full reduce-only close can use lot/minSz formatting**
   - `reduce_only_close()` now accepts `lot_sz` and `min_sz`, delegating to the same quantized path as partial TP.
   - This supports guardian/local stop callers that need exchange-valid full-close sizes.

3. **Version/report consistency**
   - `system_version` bumped to `v2.0.1-entry-stop-observability-and-close-quantization`.
   - `strategy_tag` bumped to `mi_v2_0_1_regime_adaptive_maincoin`.
   - Version-string regressions updated.

## Verification

```bash
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m pytest -q tests/mi/test_execution.py -o 'addopts='
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_healthcheck.py
```

Observed: `test_execution.py` 6 passed; full unittest suite 76 tests passed; healthcheck exit 0 and silent.

## Residual observation

A future patch should wire `lot_sz/min_sz` into every guardian `reduce_only_close()` call site after a careful live-position metadata review. The execution API is now ready for that without changing trade thresholds.