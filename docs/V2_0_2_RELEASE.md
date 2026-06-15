# Hermes Mi v2.0.2 — Trend Wear Exit-Loss-Only Bugfix

Date: 2026-06-14

## Scope

Patch release over v2.0.1. No strategy-threshold, leverage, position-count, or risk-budget increase.

## Fixes

1. **TrendWearGovernor no longer counts trend entry fees as losses**
   - v2.0.1 counted any `trend_confirmed` fill with `fillPnl + fee < 0` as a loss.
   - Entry fills commonly have `fillPnl=0` and a negative fee, which polluted `trend_loss_count_*` and could force `wear_level=3` / WAIT.
   - v2.0.2 excludes `fill_role=entry` / `order_role=entry` rows from trend wear losses.

2. **Trend wear loss counting is exit/closed-trade oriented**
   - Explicit `fill_role=exit` or `order_role=exit` rows are counted when net realized PnL after fees is negative.
   - Legacy role-less rows are still supported only when they have non-zero realized PnL.
   - Legacy fee-only rows (`fillPnl=0` plus negative `fee`) are ignored.
   - Position-side filtering now uses `posSide` first and falls back to `side` only when the lifecycle role makes the direction unambiguous.

3. **Version/report consistency**
   - `system_version` bumped to `v2.0.2-trend-wear-exit-loss-only`.
   - `strategy_tag` bumped to `mi_v2_0_2_regime_adaptive_maincoin`.
   - Package `__version__` bumped to `2.0.2`.

## Regression coverage

Added tests for:

- trend entry fee rows not increasing `loss_count`;
- trend exit loss rows being counted;
- role-less legacy fee-only rows being ignored;
- role-less legacy non-zero realized losses remaining counted.

## Verification

```bash
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
```

`mi_live_cycle.py` was intentionally not run because it can place live orders.
