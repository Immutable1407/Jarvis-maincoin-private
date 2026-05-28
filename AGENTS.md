# Jarvis Mi Agent Guide

## Scope and red lines

- Project: Hermes Mi maincoin perpetual strategy at `/root/jarvis-mi`.
- Account: dedicated OKX subaccount UID `845800098641991226`; expected `mainUid=621655308511150593`.
- Credentials: only read `HERMES_MI_OKX_*` from `/root/.hermes/.env`. Never use `OKX_*` or `OKX_SUB_*` here.
- Instruments: `BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `SOL-USDT-SWAP`, `BNB-USDT-SWAP` only.
- Runtime data under `data/` and reports under `reports/` are not committed.
- LLMs do not enter the hot path. Strategy loops are pure Python.

## v1.0.0 live gates

- Strategy tag: `mi_v1_0_0_initial_complete`.
- `active_max_positions=1` live by default.
- Second-position and rotation modules exist but remain disabled by default.
- Market-state gate blocks new entries during crash/no-trade states.
- Dynamic risk engine adjusts leverage/margin/loss cap from market state, signal quality, volatility, and resonance.
- Guardian enforces local hard stop, breakeven state, partial TP, and trailing state. Original exchange-side hard stop remains placed on entry.
- Fill sync, snapshots, ledgers, and daily briefs are runtime-private.

## Commands

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_healthcheck.py
python3 scripts/mi/mi_guardian.py
python3 scripts/mi/mi_live_cycle.py  # can place a small live order if v1.0.0 signal passes
python3 scripts/mi/mi_sync_fills.py
python3 scripts/mi/mi_daily_review.py
```

## Cron jobs

- `bc97ef299d9f` — Hermes Mi v1.0.0 maincoin live cycle, every 15m, local, `jarvis_mi_live_cycle.sh`.
- `dcb5a389e2d4` — Hermes Mi guardian, every 5m, local, `jarvis_mi_guardian.sh`.
- `4d7fbee50ff9` — Hermes Mi healthcheck, every 120m, local, `jarvis_mi_healthcheck.sh`.
- `aded3c6554f3` — Hermes Mi fill sync, every 10m, local, `jarvis_mi_sync_fills.sh`.
- `65b8d9feb0b3` — Hermes Mi daily maincoin brief, 21:00 UTC+8, delivered to origin chat, `jarvis_mi_daily_review.sh`.

## GitHub sync

Remote uses the existing Jarvis SSH alias:

```bash
git remote set-url origin git@github.com-jarvis:Immutable1407/Jarvis-maincoin-private.git
git push
```

Do not use bare `git@github.com:` unless the key is added to the default host.

## Secrets

Never commit secrets or runtime trading/account data. Private GitHub is an archive, not a secret vault. `.gitignore` excludes `/data/` and `/reports/`.
