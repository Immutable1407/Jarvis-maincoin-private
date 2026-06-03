# Hermes Mi v1.4.0 Release

Version: `v1.4.0-lane-attribution-correlated-short-governor`
Strategy tag: `mi_v1_4_0_lane_attribution_correlated_short_governor`

## Scope

- Maincoin-only Hermes Mi release over v1.3.0.
- Live deployment uses the existing active Hermes cron wrappers; the cron cadence and Feishu routing are unchanged except job names now reflect v1.4.0.

## Changes

- Lane attribution now propagates `strategy_lane`, `near_miss_pass`, `expected_net_pct`, and `expected_tp1_net_pct` through decisions, entry records, fill-sync enrichment, and the daily brief where available.
- Near-miss loosening is feedback-gated: recent negative lane samples or repeated same instrument+side local stops disable near-miss during the cooldown window. If feedback state is unavailable, the gate fails closed and does not loosen thresholds.
- Correlated same-direction governor blocks low-quality second same-direction additions unless candidate score is at least 84 or the candidate is `trend_confirmed`. It does not raise max positions or margin caps and does not globally disable shorts.
- Guardian exits now record same instrument+side cooldowns by reason: local stop 4h, breakeven 2h, trailing 1h. TP2/MFE-style exits do not create a penalty cooldown.
- Daily brief adds realized net after fees, deduped fill count, lane/near-miss summary, top rejection reason over the last 100 decisions, guardian exit counts, and current positions/UPL from the latest decision snapshot.

## Verification

Safe commands only:

```bash
cd /root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 -m pytest -q tests/mi/test_v1_3_adaptive_lane.py tests/mi/test_fills_v1_3.py tests/mi/test_v1_4_lane_attribution_governors.py
python3 scripts/mi/mi_healthcheck.py
python3 scripts/mi/mi_sync_fills.py
python3 scripts/mi/mi_daily_review.py
```

Do not use `scripts/mi/mi_live_cycle.py` as a verification command because it can place live orders.
