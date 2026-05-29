# Hermes Mi v1.2.0 Maincoin Strategy Architecture

## Purpose

Hermes Mi is a dedicated OKX maincoin perpetual strategy isolated from BTC-AHR999 and Jarvis v4 altcoin trading. v1.2.0 upgrades the maincoin engine from a single conservative breakout lane to a three-lane, percent-profit-gated system for BTC/ETH/SOL/BNB only.

## Account and instrument boundaries

- Expected OKX UID: `845800098641991226`
- Expected mainUid: `621655308511150593`
- Credential prefix: `HERMES_MI_OKX_*`
- Forbidden credential prefixes in this project: `OKX_*`, `OKX_SUB_*`
- Allowed instruments:
  - `BTC-USDT-SWAP`
  - `ETH-USDT-SWAP`
  - `SOL-USDT-SWAP`
  - `BNB-USDT-SWAP`

Every private read/write path must verify UID/mainUid before acting. Non-whitelisted SWAP positions are abnormal and should fail/alert.

## Live gates

- `strategy_tag = mi_v1_2_0_three_lane_percent_engine`
- `active_max_positions = 2`
- `enable_second_position = True`
- `enable_rotation = False`
- `portfolio_margin_cap_pct = 0.60`
- `single_position_margin_cap_pct = 0.35`
- `second_position_margin_cap_pct = 0.30`
- `allow_mixed_direction_portfolio = False`
- `altcoin_profit_baseline_pct = 0.012`
- `maincoin_profit_baseline_multiplier = 1.35`
- `min_expected_net_profit_pct = 0.0162`
- margin mode: cross
- hot path: deterministic Python only, no LLM order decisioning

The profit baseline is dynamic percentage-based, not fixed USDT. Candidate expected net profit must scale with current equity and exceed the altcoin equity-share baseline by multiplier because the maincoin equity-curve slope target is higher.

## Signal lanes

- `trend_confirmed`: 1H trend confirmation plus 15m breakout/reclaim path. This preserves the original conservative maincoin logic.
- `trend_probe`: early trend pullback/reclaim or reject path, intended to reduce no-MFE late entries by entering earlier with lane-specific risk.
- `range_swing`: chop/range edge trades when maincoins are bounded and BTC bias is not strongly against the trade.

The live cycle evaluates ranked candidates and now continues to later candidates if the top candidate fails portfolio or percent-profit gates.

## Risk ladder

- paused: 0x, 0% margin, no new entries
- range_swing: about 6x, 16% margin, about 1.2% max loss before volatility/resonance multipliers
- trend_probe: about 8x, 14% margin, about 1.4% max loss before volatility/resonance multipliers
- reduced: 5x-8x, 12%-18% margin, 1.0%-1.8% max loss
- normal: about 10x, 25% margin, about 3% max loss
- strong: up to 12x, 32%-35% margin, about 3.5%-4.0% max loss

High volatility (`ATR / price > 3.5%`) caps leverage to 8x and scales margin/loss budgets down by 40%.

## Live cycle data flow

`python3 scripts/mi/mi_live_cycle.py`:

1. Load config and verify Hermes Mi UID/mainUid.
2. Read USDT equity and open positions.
3. Reject non-whitelisted SWAP positions.
4. Load whitelisted instrument metadata.
5. Read 1h and 15m candles for all four instruments.
6. Compute BTC bias.
7. Classify market state:
   - `btc_regime`
   - `maincoin_regime`
   - `direction_bias`
   - `frequency_mode`
   - `risk_budget`
8. Compute four-maincoin resonance:
   - aligned long/short
   - BTC/alt divergence
   - mixed state
9. Score three-lane signals with lane-specific reason codes.
10. Apply market-state direction gate.
11. Sort candidates by score and evaluate them in order.
12. Apply portfolio gate: max two positions, no duplicate symbol, no mixed long/short by default.
13. Compute lane-aware dynamic risk decision.
14. Preview expected full-trade net profit as a percentage of equity and require it to exceed the dynamic maincoin baseline.
15. Compute size and enforce portfolio margin guard inside `execute_entry`.
16. Submit market entry and standalone reduce-only stop only if all gates pass.
17. Save local snapshot and decision ledger.

## Guardian and exits

`python3 scripts/mi/mi_guardian.py` runs every 5m and manages open positions:

- account guard and instrument whitelist guard;
- local ATR/structure hard stop;
- breakeven state after sufficient MFE;
- partial take profit with reduce-only orders;
- trailing state after profits mature;
- per-action error isolation so one failed partial TP does not stop guardian protection;
- exit state keyed by instrument, direction, and average price to avoid stale state reuse.

The entry path still places an exchange-side standalone hard stop. Breakeven/trailing are local guardian-enforced; exchange-side cancel/replace hardening is future work.

## Fill sync and reports

- `scripts/mi/mi_sync_fills.py`: syncs OKX fills every 10m to local ledgers.
- `scripts/mi/mi_daily_review.py`: emits a concise daily maincoin brief with v1.2.0 status, max positions, portfolio margin estimate, and blocked decision count.
- Runtime data lives under `/root/jarvis-mi/data/` and `/root/jarvis-mi/reports/` and must never be committed.

## Cron jobs

- `bc97ef299d9f` — live cycle, every 15m, local delivery.
- `dcb5a389e2d4` — guardian, every 5m, local delivery.
- `4d7fbee50ff9` — healthcheck, every 120m, local delivery.
- `aded3c6554f3` — fill sync, every 10m, local delivery.
- `65b8d9feb0b3` — daily maincoin brief, 21:00 UTC+8, delivered to Feishu.

## Verification

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_healthcheck.py
python3 scripts/mi/mi_guardian.py
python3 scripts/mi/mi_live_cycle.py
python3 scripts/mi/mi_sync_fills.py
python3 scripts/mi/mi_daily_review.py
```

`mi_live_cycle.py` can place a live order if a strict lane signal passes. Pause the live-cycle cron before manual testing if no new entries are desired.

## GitHub release

- Private repo: `Immutable1407/Jarvis-maincoin-private`
- Remote: `git@github.com-jarvis:Immutable1407/Jarvis-maincoin-private.git`
- Release tag: `v1.2.0`

Before pushing, scan staged files for secrets and confirm no `/data/`, `/reports/`, `.env*`, `.jsonl`, account snapshots, fills, or ledgers are committed.
