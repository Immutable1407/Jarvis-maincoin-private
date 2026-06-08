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
print([{k:p.get(k) for k in ['instId','pos','posSide','mgnMode','avgPx','markPx','upl','imr','lever']} for p in c.open_positions()])
PY
```

## Check cron jobs

```bash
hermes cron list --all
```

Relevant jobs:

- `bc97ef299d9f` — v1.4.2 live cycle, every 15m, local.
- `dcb5a389e2d4` — guardian, every 5m, local.
- `4d7fbee50ff9` — healthcheck, every 120m, local.
- `aded3c6554f3` — fill sync, every 10m, local.
- `65b8d9feb0b3` — daily maincoin brief, 21:00 UTC+8, Feishu.
- `f65da2f01c13` — combined maincoin+altcoin weekly summary, Sunday 22:00 UTC+8, Feishu; lives in Hermes cron and covers both Jarvis v4 and Hermes Mi.

Feishu should normally receive only BTC-AHR999 DCA, Jarvis v4 daily recap, Hermes Mi daily brief, and the Sunday combined weekly summary. Maincoin execution/guardian/health/fill-sync outputs stay `local`.

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
hermes cron pause aded3c6554f3
hermes cron pause 65b8d9feb0b3
```

## Resume Hermes Mi trading

```bash
hermes cron resume 4d7fbee50ff9
hermes cron resume dcb5a389e2d4
hermes cron resume aded3c6554f3
hermes cron resume 65b8d9feb0b3
hermes cron resume bc97ef299d9f
```

## Manual verification

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_healthcheck.py
python3 scripts/mi/mi_guardian.py
python3 scripts/mi/mi_sync_fills.py
python3 scripts/mi/mi_attribution_audit.py
python3 scripts/mi/mi_daily_review.py
```

`python3 scripts/mi/mi_live_cycle.py` can place a live order if a strict v1.4.2 lane signal passes portfolio, guardian-cooldown, dynamic percent-profit, feedback near-miss, and correlated same-direction governor gates. Do not use it for read-only verification.

## Attribution audit (new in v1.4.2)

Inspect attribution without touching live orders:

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 scripts/mi/mi_attribution_audit.py --day $(TZ=Asia/Shanghai date +%F)
python3 scripts/mi/mi_attribution_audit.py --day $(TZ=Asia/Shanghai date +%F) --json
```

## Logs, ledgers, and reports

Runtime ledgers and reports are local-only and not committed:

```bash
tail -n 20 /root/jarvis-mi/data/mi/ledgers/decisions.jsonl
tail -n 20 /root/jarvis-mi/data/mi/ledgers/trades.jsonl
tail -n 20 /root/jarvis-mi/data/mi/ledgers/guardian.jsonl
tail -n 20 /root/jarvis-mi/data/mi/ledgers/healthcheck.jsonl
tail -n 20 /root/jarvis-mi/data/mi/ledgers/fills.jsonl
ls -R /root/jarvis-mi/data/mi/snapshots | tail
ls /root/jarvis-mi/reports/mi/daily
```

## GitHub sync

Remote must use:

```bash
git@github.com-jarvis:Immutable1407/Jarvis-maincoin-private.git
```

Safe sync checklist:

```bash
cd /root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
git status --short
git add AGENTS.md README.md docs jarvis_mi scripts tests .gitignore
git diff --cached --name-only
# confirm no /data, /reports, .env*, .jsonl, account snapshots, fills, or ledgers are staged
git commit -m 'feat(mi): release v1.4.0 lane attribution governors'
git push
```

Private GitHub is not a secret vault. Never commit credentials or runtime trading/account data.
