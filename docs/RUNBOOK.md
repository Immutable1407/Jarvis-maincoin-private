# Hermes Mi Runbook

## Check live state

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 scripts/mi/mi_healthcheck.py
python3 - <<'PY'
from jarvis_mi.config_mi import MiConfig
from jarvis_mi.okx_mi_client import OKXMiClient
from jarvis_mi.account_guard import assert_mi_account
cfg = MiConfig.from_env()
c = OKXMiClient(cfg)
print(assert_mi_account(c, cfg))
print(c.usdt_equity())
print([{k:p.get(k) for k in ['instId','pos','posSide','mgnMode','avgPx','markPx','upl']} for p in c.open_positions()])
PY
```

## Check cron jobs

```bash
hermes cron list --all
```

Relevant jobs:

- `bc97ef299d9f` — live cycle
- `dcb5a389e2d4` — guardian
- `4d7fbee50ff9` — healthcheck

## Pause Hermes Mi trading

Pause new entries first:

```bash
hermes cron pause bc97ef299d9f
```

Keep guardian running until all positions are flat. To pause all Hermes Mi jobs:

```bash
hermes cron pause bc97ef299d9f
hermes cron pause dcb5a389e2d4
hermes cron pause 4d7fbee50ff9
```

## Resume Hermes Mi trading

```bash
hermes cron resume 4d7fbee50ff9
hermes cron resume dcb5a389e2d4
hermes cron resume bc97ef299d9f
```

## Logs and ledgers

Runtime ledgers are local-only and not committed:

```bash
tail -n 20 /root/jarvis-mi/data/mi/ledgers/decisions.jsonl
tail -n 20 /root/jarvis-mi/data/mi/ledgers/trades.jsonl
tail -n 20 /root/jarvis-mi/data/mi/ledgers/guardian.jsonl
tail -n 20 /root/jarvis-mi/data/mi/ledgers/healthcheck.jsonl
```

## GitHub sync

```bash
cd /root/jarvis-mi
git status --short
git add AGENTS.md README.md docs jarvis_mi scripts tests .gitignore
git commit -m 'docs: update Hermes Mi runbook'
git push
```

Remote must use:

```bash
git@github.com-jarvis:Immutable1407/Jarvis-maincoin-private.git
```
