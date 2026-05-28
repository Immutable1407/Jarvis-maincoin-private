# Jarvis Maincoin Private / Hermes Mi

Private repository for the Hermes Mi maincoin perpetual strategy.

## Current version

`v1.0.0-initial-complete` is deployed on the VPS at `/root/jarvis-mi`.

## Scope

- Dedicated OKX subaccount: Hermes Mi
- Account UID: `845800098641991226`
- Instruments: `BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `SOL-USDT-SWAP`, `BNB-USDT-SWAP`
- Timeframes: 1h market/trend state, 15m trigger/guardian checks
- Hot path: deterministic Python only; no LLM in order execution

## v1.0.0 live gates

- Active live positions: 1
- Code supports second-position/rotation modules, but both remain disabled by default
- Margin mode: cross
- Dynamic risk engine: 5x-20x depending on market state, signal quality, volatility, and resonance
- Max theoretical stop loss remains capped by risk engine / sizing guard
- Market-state gate blocks new entries during crash/no-trade states
- Resonance engine scores BTC/ETH/SOL/BNB alignment/divergence
- Guardian manages local hard stop, breakeven state, partial TP, and trailing state
- Runtime snapshots, fills, ledgers, and daily briefs are local-only and ignored by Git

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

`mi_live_cycle.py` can place a small live order when a strict v1.0.0 signal passes.

## Cron jobs

- `bc97ef299d9f` — v1.0.0 live cycle, every 15m, local
- `dcb5a389e2d4` — guardian, every 5m, local
- `4d7fbee50ff9` — healthcheck, every 120m, local
- `aded3c6554f3` — fill sync, every 10m, local
- `65b8d9feb0b3` — daily maincoin brief, 21:00 UTC+8, origin chat

## Secrets

Secrets are never committed. Runtime credentials live in `/root/.hermes/.env` using `HERMES_MI_OKX_*` variables. Runtime ledgers, snapshots, fills, reports, account data, and daily briefs under `data/` and `reports/` are excluded from Git.
