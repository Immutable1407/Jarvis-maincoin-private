# Hermes Mi v1.2.1 Release — Daily Report Consistency Patch

Date: 2026-05-29

## Scope

Patch release after today's Hermes Mi daily brief showed stale v1.1.0 wording while the live strategy tag was already v1.2.0 three-lane percent engine.

## Fixes

- `jarvis_mi/config_mi.py`
  - Adds explicit `system_version = "v1.2.1-report-consistency"`.
- `jarvis_mi/performance.py`
  - Daily brief now reports the current v1.2.x three-lane percent-baseline system instead of stale v1.1.0 dynamic two-slot wording.
  - Adds signal lane names and percent net-profit threshold to the brief.
- Tests
  - Adds regression coverage to prevent future stale-version text in the daily report.

## Trading impact

No trading hot-path behavior changed. This patch only changes reporting/version metadata.

## Verification

Run:

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_daily_review.py
```
