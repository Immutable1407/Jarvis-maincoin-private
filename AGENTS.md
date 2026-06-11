# Jarvis Mi Agent Guide

## Scope and red lines

- Project: Hermes Mi maincoin perpetual strategy at `/root/jarvis-mi`.
- Account: dedicated OKX subaccount UID `845800098641991226`; expected `mainUid=621655308511150593`.
- Credentials: only read `HERMES_MI_OKX_*` from `/root/.hermes/.env`. Never use `OKX_*` or `OKX_SUB_*` here.
- Instruments: `BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `SOL-USDT-SWAP`, `BNB-USDT-SWAP` only.
- Runtime data under `data/` and reports under `reports/` are not committed.
- LLMs do not enter the hot path. Strategy loops are pure Python.

## v2.0.0 current state

- **v2.0.0 is the current live version** — regime-adaptive maincoin foundation replacing the v1.x trend-confirmed-first hot path.
- Strategy tag: `mi_v2_0_0_regime_adaptive_maincoin`.
- Hot path: `MarketStructureClassifier -> TrendWearGovernor -> ModeRouter -> SecondConfirmationGate / LimitedRangeSurviveEngine -> RiskLadderV2 -> existing portfolio/profit/correlation/execution guards`.
- TREND normal risk requires second confirmation; TRANSITION is probe-only; CHOP defaults to WAIT unless range quality/boundary/fee gates pass; WAIT disables new entries.
- Trend wear and drawdown logic can only reduce risk or block entries; classifier/router errors fail closed to WAIT.
- v1.4.2/v1.4.3 attribution and OKX stop-algo schema fixes are retained.
- Current first live v2 observation: classifier may label trend, but accumulated wear can demote mode to WAIT and block new entries.

## Important historical live gates

- v1.4.3: OKX entry stop-loss algo schema hotfix using `slTriggerPx/slOrdPx/slTriggerPxType`; no trading thresholds changed.
- v1.4.2: cold-path attribution layer `jarvis_mi/attribution.py`, `scripts/mi/mi_attribution_audit.py`, enriched fills, and daily brief attribution sections.
- v1.4.1/v1.4.0: lane attribution, feedback-based near-miss cooldown, correlated same-direction governor, Guardian exit cooldowns, richer daily brief.
- v1.2.x/v1.3.x: three signal lanes and lane-specific expected-net thresholds: trend_confirmed 1.50%, trend_probe 1.45%, range_swing 1.38% of equity.

## Invariants

- `active_max_positions=2` live by default.
- Second position is enabled; rotation remains disabled by default.
- Portfolio margin hard cap is 60% of equity; single-position cap is 35%; second-position cap is 30%.
- Mixed long/short portfolios are blocked by default.
- Guardian enforces local hard stop, breakeven state, partial TP, and trailing state. Original exchange-side hard stop remains placed on entry.
- Fill sync, snapshots, ledgers, counterfactuals, and daily briefs are runtime-private.

## Docs pointer

- `docs/HERMES_MI_ARCHITECTURE.md` — current v2.0.0 architecture, data flow, gates, cron jobs.
- `docs/V2_0_0_RELEASE.md` — v2.0.0 regime-adaptive foundation release notes.
- `docs/V2_0_0_REGIME_ADAPTIVE_MAINCOIN_PLAN.md` — v2.0.0 plan and v2.1-v2.9 two-day iteration policy.
- `docs/V1_4_3_RELEASE.md` — v1.4.3 OKX stop-algo schema hotfix notes.
- `docs/V1_4_2_RELEASE.md` — v1.4.2 attribution-only release notes.
- `docs/V1_4_2_ATTRIBUTION_PLAN_DEEPSEEK.md` — v1.4.2 attribution-only upgrade plan.
- `docs/RUNBOOK.md` — operations, pause/resume, verification, GitHub sync.

## Commands

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_healthcheck.py
python3 scripts/mi/mi_guardian.py
python3 scripts/mi/mi_live_cycle.py  # can place a live order if v2 regime/mode/confirmation/risk and legacy guards pass
python3 scripts/mi/mi_sync_fills.py
python3 scripts/mi/mi_attribution_audit.py
python3 scripts/mi/mi_daily_review.py
```

## Cron jobs

- `bc97ef299d9f` — Hermes Mi v2.0.0 regime-adaptive maincoin live cycle, every 15m, local, `jarvis_mi_live_cycle.sh`.
- `dcb5a389e2d4` — Hermes Mi v2.0.0 maincoin guardian, every 5m, local, `jarvis_mi_guardian.sh`.
- `4d7fbee50ff9` — Hermes Mi v2.0.0 maincoin healthcheck, every 120m, local, `jarvis_mi_healthcheck.sh`.
- `aded3c6554f3` — Hermes Mi v2.0.0 fill sync, every 10m, local, `jarvis_mi_sync_fills.sh`.
- `65b8d9feb0b3` — Hermes Mi v2.0.0 daily maincoin brief, 21:00 UTC+8, delivered to Feishu, `jarvis_mi_daily_review.sh`.
- `f65da2f01c13` — combined maincoin+altcoin weekly summary, Sunday 22:00 UTC+8, delivered to Feishu; Hermes cron job, not a project script.

Feishu notification policy is summary-only: BTC-AHR999 DCA, Jarvis v4 daily recap, Hermes Mi daily brief, and Sunday combined weekly summary. Hermes Mi live-cycle/guardian/health/fill-sync jobs stay local.

## GitHub sync

Remote uses the existing Jarvis SSH alias:

```bash
git remote set-url origin git@github.com-jarvis:Immutable1407/Jarvis-maincoin-private.git
git push
```

Do not use bare `git@github.com:` unless the key is added to the default host.

## Secrets

Never commit secrets or runtime trading/account data. Private GitHub is an archive, not a secret vault. `.gitignore` excludes `/data/` and `/reports/`.
