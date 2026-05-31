# Hermes Mi v1.3.0 — Adaptive Lane Profit Engine

Date: 2026-05-31

## Why

Recent two-day data showed the v1.2 static percent-profit gate was rejecting almost all candidates. Many lane candidates were near misses: the best previewed net profit was just below the 1.62% global threshold. At the same time, fill sync duplicated OKX fills heavily and guardian trailing state could loosen on long positions.

## Changes

- Bumped `system_version` to `v1.3.0-adaptive-lane-profit-engine`.
- Bumped `strategy_tag` to `mi_v1_3_0_adaptive_lane_profit_engine`.
- Added lane-aware profit thresholds:
  - `trend_confirmed`: 1.50% equity expected net.
  - `trend_probe`: 1.45% equity expected net.
  - `range_swing`: 1.38% equity expected net.
- Added controlled near-miss pass:
  - expected net must be at least 92% of lane threshold;
  - TP1 expected net must be fee-positive;
  - candidate score must be at least 66;
  - risk engine must not be paused.
- Fill sync now dedupes fills by `tradeId`/`billId`/composite key and persists `state/fill_sync_seen.json`.
- Guardian trailing stop state is monotonic:
  - long trailing stops never move downward;
  - short trailing stops never move upward.
- Daily brief now reports v1.3 lane thresholds and near-miss condition.
- Stale `no_v1_1_candidate` reason renamed to version-neutral `no_candidate`.
- MI entry scripts now self-bootstrap project root, so direct `python3 scripts/mi/*.py` execution matches cron wrapper behavior.
- Package `__version__` is synchronized to `1.3.0`.
- Fill-sync seen-key retention now trims by first-seen order instead of lexicographic key order.

## Safety

This is not a blind loosening release. Portfolio gates, market-state gates, risk engine pause, UID/account isolation, max two positions, mixed-direction block, and margin caps remain unchanged.

## Verification

```bash
cd /root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 -m pytest -q tests/mi/test_v1_3_adaptive_lane.py tests/mi/test_fills_v1_3.py
```
