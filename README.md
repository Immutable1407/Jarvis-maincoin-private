# Jarvis Maincoin Private / Hermes Mi

Private repository for the Hermes Mi maincoin perpetual strategy.

## Current version

`v1.1.0-dynamic-two-slot` is deployed on the VPS at `/root/jarvis-mi`.

## Scope

- Dedicated OKX subaccount: Hermes Mi
- Account UID: `845800098641991226`
- Instruments: `BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `SOL-USDT-SWAP`, `BNB-USDT-SWAP`
- Timeframes: 1h market/trend state, 15m trigger/guardian checks
- Hot path: deterministic Python only; no LLM in order execution

## v1.1.0 live gates

- Active live positions: max 2
- Second position enabled; rotation remains disabled by default
- Margin mode: cross
- Portfolio margin hard cap: 60% of equity across both positions
- Single-position margin cap: 35% of equity
- Second-position margin cap: 30% of equity
- Mixed long/short portfolios are blocked by default
- Dynamic risk engine: higher margin with moderate 3x-12x leverage, depending on market state, signal quality, volatility, and resonance
- Max theoretical stop loss remains capped by risk engine / sizing guard
- Market-state gate blocks new entries during crash/no-trade states
- Resonance engine scores BTC/ETH/SOL/BNB alignment/divergence
- Guardian manages local hard stop, breakeven state, partial TP, and trailing state
- Runtime snapshots, fills, ledgers, and daily briefs are local-only and ignored by Git

## Docs

- `docs/HERMES_MI_ARCHITECTURE.md` — current v1.1.0 architecture and live gates.
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

`mi_live_cycle.py` can place a live order when a strict v1.1.0 signal passes and all portfolio margin gates allow it.

## Cron jobs

- `bc97ef299d9f` — v1.1.0 live cycle, every 15m, local
- `dcb5a389e2d4` — guardian, every 5m, local
- `4d7fbee50ff9` — healthcheck, every 120m, local
- `aded3c6554f3` — fill sync, every 10m, local
- `65b8d9feb0b3` — daily maincoin brief, 21:00 UTC+8, Feishu

## Secrets

Secrets are never committed. Runtime credentials live in `/root/.hermes/.env` using `HERMES_MI_OKX_*` variables. Runtime ledgers, snapshots, fills, reports, account data, and daily briefs under `data/` and `reports/` are excluded from Git.
