# Hermes Mi v1.2.0 — Three-Lane Percent Profit Engine

Date: 2026-05-29

## Purpose

Move maincoin trading from a single conservative breakout lane to a three-lane profit engine while keeping the profit target dynamic as a percentage of equity.

Sir's correction: the 0.5U reference is not a fixed maincoin target. It was an altcoin small-account equity-share observation. Maincoin per-trade expected net profit should scale with account equity and should exceed the altcoin per-trade equity-share baseline because the desired maincoin equity-curve slope is steeper.

## Changes

- `strategy_tag = mi_v1_2_0_three_lane_percent_engine`.
- Adds percent baseline config:
  - `altcoin_profit_baseline_pct = 0.012`
  - `maincoin_profit_baseline_multiplier = 1.35`
  - `min_expected_net_profit_pct = 0.0162`
- Adds three signal lanes:
  - `trend_confirmed`: existing 1H trend + 15m breakout path.
  - `trend_probe`: early trend pullback/reclaim or reject with smaller/faster profile.
  - `range_swing`: BTC/maincoin chop range-edge trades.
- Risk engine now receives `strategy_lane` and adjusts risk mode by lane.
- Live cycle previews expected net profit before entry and blocks candidates whose expected full-trade net profit percentage is below the dynamic percent baseline.

## Operational rule

No fixed 0.5U baseline. Maincoin entries must justify themselves as a percentage of current equity. As equity grows, required USDT profit grows automatically.

## Verification

Run:

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_healthcheck.py
```
