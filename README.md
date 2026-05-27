# Jarvis Maincoin Private / Hermes Mi

Private repository for the Hermes Mi maincoin perpetual strategy.

## Current version

`v0.1.0` live bootstrap is deployed on the VPS at `/root/jarvis-mi`.

## Scope

- Dedicated OKX subaccount: Hermes Mi
- Account UID: `845800098641991226`
- Instruments: `BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `SOL-USDT-SWAP`, `BNB-USDT-SWAP`
- Timeframes: 1h trend filter, 15m trigger/guardian checks
- Delivery: local cron only; no Feishu push for v0.x

## v0.1 limits

- Max positions: 1
- Margin mode: cross
- Leverage: 20x
- Margin per trade: 6%, hard cap 8%
- Max theoretical stop loss: 1.2% equity
- No range trading
- No rotation/replacement
- No pyramiding
- No partial TP in v0.1
- No LLM in the hot path

## Runtime commands

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_healthcheck.py
python3 scripts/mi/mi_guardian.py
python3 scripts/mi/mi_live_cycle.py
```

`mi_live_cycle.py` can place a small live order when a strict v0.1 signal passes.

## Cron jobs

- `bc97ef299d9f` — live cycle, every 15m, local
- `dcb5a389e2d4` — guardian, every 5m, local
- `4d7fbee50ff9` — healthcheck, every 120m, local

## Secrets

Secrets are never committed. Runtime credentials live in `/root/.hermes/.env` using `HERMES_MI_OKX_*` variables. Runtime ledgers and reports under `data/mi/` and `reports/mi/` are excluded from Git.
