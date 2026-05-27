# Jarvis Mi Agent Guide

## Scope and red lines

- Project: Hermes Mi maincoin perpetual strategy at `/root/jarvis-mi`.
- Account: dedicated OKX subaccount UID `845800098641991226`; expected `mainUid=621655308511150593`.
- Credentials: only read `HERMES_MI_OKX_*` from `/root/.hermes/.env`. Never use `OKX_*` or `OKX_SUB_*` here.
- Instruments: `BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `SOL-USDT-SWAP`, `BNB-USDT-SWAP` only.
- Runtime data under `data/mi/` and reports under `reports/mi/` are not committed.
- LLMs do not enter the hot path. Strategy loops are pure Python.

## v0.1 live limits

- `max_positions=1`
- `td_mode=cross`
- `default_leverage=20`
- `margin_pct=0.06`, hard cap `0.08`
- max theoretical stop loss `1.2%` of equity
- no range trading, no rotation, no pyramiding, no partial TP in v0.1

## Commands

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_healthcheck.py
python3 scripts/mi/mi_guardian.py
python3 scripts/mi/mi_live_cycle.py  # can place a small live order if v0.1 signal passes
```

## Cron jobs

- `bc97ef299d9f` — Hermes Mi v0.1 maincoin live cycle, every 15m, local, `jarvis_mi_live_cycle.sh`.
- `dcb5a389e2d4` — Hermes Mi v0.1 maincoin guardian, every 5m, local, `jarvis_mi_guardian.sh`.
- `4d7fbee50ff9` — Hermes Mi v0.1 maincoin healthcheck, every 120m, local, `jarvis_mi_healthcheck.sh`.

No Feishu delivery for v0.x.

## GitHub sync

Remote uses the existing Jarvis SSH alias:

```bash
git remote set-url origin git@github.com-jarvis:Immutable1407/Jarvis-maincoin-private.git
git push
```

Do not use bare `git@github.com:` unless the key is added to the default host.
