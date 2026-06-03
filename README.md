# Jarvis Maincoin Private / Hermes Mi

Private repository for the Hermes Mi maincoin perpetual strategy.

## Current version

`v1.4.1-lane-attribution-correlated-short-governor` is deployed on the VPS at `/root/jarvis-mi`.

## Scope

- Dedicated OKX subaccount: Hermes Mi
- Account UID: `845800098641991226`
- Instruments: `BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `SOL-USDT-SWAP`, `BNB-USDT-SWAP`
- Timeframes: 1h market/trend state, 15m trigger/guardian checks
- Hot path: deterministic Python only; no LLM in order execution

## v1.4.1 live gates

- Active live positions: max 2
- Strategy tag: `mi_v1_4_0_lane_attribution_correlated_short_governor`
- Three lanes: `trend_confirmed`, `trend_probe`, `range_swing`
- Profit baseline is lane-aware and percentage-based, not fixed USDT: trend_confirmed 1.50%, trend_probe 1.45%, range_swing 1.38% of equity, with a controlled near-miss pass only when fee-positive, risk gates are clean, and lane/guardian feedback cooldowns allow it
- Same-direction second position is correlation-governed: low-quality additions are blocked unless score ≥84 or lane is `trend_confirmed`
- Second position enabled; rotation remains disabled by default
- Margin mode: cross
- Portfolio margin hard cap: 60% of equity across both positions
- Single-position margin cap: 35% of equity
- Second-position margin cap: 30% of equity
- Mixed long/short portfolios are blocked by default
- Dynamic risk engine: higher margin with moderate 3x-12x leverage, depending on market state, signal quality, volatility, resonance, and lane
- Max theoretical stop loss remains capped by risk engine / sizing guard
- Market-state gate blocks new entries during crash/no-trade states
- Resonance engine scores BTC/ETH/SOL/BNB alignment/divergence
- Guardian manages local hard stop, breakeven state, partial TP, and trailing state
- Fill sync dedupes OKX fills; guardian trailing state is monotonic and must not loosen stops; local_stop/breakeven/trailing exits create same instrument+side cooldowns
- Runtime snapshots, fills, ledgers, and daily briefs are local-only and ignored by Git

## Docs

- `docs/HERMES_MI_ARCHITECTURE.md` — current v1.4.1 architecture and live gates.
- `docs/V1_4_0_RELEASE.md` — v1.4.1 lane attribution + correlated same-direction governor release notes.
- `docs/V1_3_0_RELEASE.md` — v1.3.0 adaptive lane profit engine release notes.
- `docs/V1_2_1_RELEASE.md` — v1.2.1 report consistency patch notes.
- `docs/V1_2_0_RELEASE.md` — v1.2.0 three-lane percent-engine release notes.
- `docs/RUNBOOK.md` — operations, cron, pause/resume, verification, GitHub sync.
- `docs/HERMES_MI_V0_1_INFRA_PLAN.md` — historical v0.1 bootstrap design.

## Runtime commands

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

`mi_live_cycle.py` can place a live order when a strict v1.4.1 lane signal passes and all portfolio/profit/correlation gates allow it.

## Cron jobs

- `bc97ef299d9f` — v1.4.1 live cycle, every 15m, local
- `dcb5a389e2d4` — v1.4.1 guardian, every 5m, local
- `4d7fbee50ff9` — v1.4.1 healthcheck, every 120m, local
- `aded3c6554f3` — v1.4.1 fill sync, every 10m, local
- `65b8d9feb0b3` — v1.4.1 daily maincoin brief, 21:00 UTC+8, Feishu

Feishu notification policy is summary-only: BTC-AHR999 DCA, Jarvis v4 daily recap, this Hermes Mi daily brief, and the Sunday 22:00 UTC+8 combined maincoin+altcoin weekly summary. Maincoin live-cycle/guardian/health/fill-sync jobs stay local.

## Secrets

Secrets are never committed. Runtime credentials live in `/root/.hermes/.env` using `HERMES_MI_OKX_*` variables. Runtime ledgers, snapshots, fills, reports, account data, and daily briefs under `data/` and `reports/` are excluded from Git.
