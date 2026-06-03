# Jarvis Mi Agent Guide

## Scope and red lines

- Project: Hermes Mi maincoin perpetual strategy at `/root/jarvis-mi`.
- Account: dedicated OKX subaccount UID `845800098641991226`; expected `mainUid=621655308511150593`.
- Credentials: only read `HERMES_MI_OKX_*` from `/root/.hermes/.env`. Never use `OKX_*` or `OKX_SUB_*` here.
- Instruments: `BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `SOL-USDT-SWAP`, `BNB-USDT-SWAP` only.
- Runtime data under `data/` and reports under `reports/` are not committed.
- LLMs do not enter the hot path. Strategy loops are pure Python.

## v1.4.1 live gates

- Patch over v1.4.0: entry/report fail-loud hotfix; v1.4.0 kept  lane attribution, feedback-based near-miss cooldown, correlated same-direction governor, Guardian exit cooldowns, and richer daily brief.
- Strategy tag: `mi_v1_4_1_entry_report_fail_loud_hotfix`.
- Lane-specific expected-net thresholds remain: trend_confirmed 1.50%, trend_probe 1.45%, range_swing 1.38% of equity.
- Controlled near-miss pass requires ≥92% of lane threshold, fee-positive TP1 preview, candidate score ≥66, non-paused risk engine, and no lane/guardian feedback cooldown.
- Same-direction second position requires score ≥84 or `trend_confirmed`; max positions and margin caps are unchanged.
- Fill sync dedupes by `tradeId`/`billId`/composite key into `data/mi/state/fill_sync_seen.json`.
- Guardian trailing stop state remains monotonic and now records local-stop/breakeven/trailing cooldowns for same instrument+side.

## v1.2.1 live gates (previous baseline)

- Patch over v1.2.0: daily report/version metadata consistency; no trading hot-path change.
- Strategy tag: `mi_v1_2_0_three_lane_percent_engine`.
- Three signal lanes are active: `trend_confirmed`, `trend_probe`, and `range_swing`.
- Profit filter is percentage-based, not fixed-USDT: maincoin expected net profit must exceed the altcoin dynamic equity-share baseline by multiplier (`altcoin_profit_baseline_pct * maincoin_profit_baseline_multiplier`).
- `active_max_positions=2` live by default.
- Second position is enabled; rotation remains disabled by default.
- Portfolio margin hard cap is 60% of equity; single-position cap is 35%; second-position cap is 30%.
- Mixed long/short portfolios are blocked by default.
- Market-state gate blocks new entries during crash/no-trade states.
- Dynamic risk engine uses higher margin with moderate 3x-12x leverage from market state, signal quality, volatility, and resonance.
- Guardian enforces local hard stop, breakeven state, partial TP, and trailing state. Original exchange-side hard stop remains placed on entry.
- Fill sync, snapshots, ledgers, and daily briefs are runtime-private.

## Docs pointer

- `docs/HERMES_MI_ARCHITECTURE.md` — current v1.4.1 architecture, data flow, gates, cron jobs.
- `docs/V1_4_1_RELEASE.md` — v1.4.1 entry/report fail-loud hotfix notes.
- `docs/V1_4_0_RELEASE.md` — v1.4.0 lane attribution + correlated short governor release notes.
- `docs/V1_3_0_RELEASE.md` — v1.3.0 adaptive lane profit engine release notes.
- `docs/V1_2_1_RELEASE.md` — v1.2.1 report consistency patch notes.
- `docs/V1_2_0_RELEASE.md` — v1.2.0 three-lane percent-engine release notes.
- `docs/RUNBOOK.md` — operations, pause/resume, verification, GitHub sync.
- `docs/HERMES_MI_V0_1_INFRA_PLAN.md` — historical v0.1 bootstrap reference only.

## Commands

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_healthcheck.py
python3 scripts/mi/mi_guardian.py
python3 scripts/mi/mi_live_cycle.py  # can place a live order if v1.4.1 signal and portfolio/profit/correlation gates pass
python3 scripts/mi/mi_sync_fills.py
python3 scripts/mi/mi_daily_review.py
```

## Cron jobs

- `bc97ef299d9f` — Hermes Mi v1.4.1 maincoin live cycle, every 15m, local, `jarvis_mi_live_cycle.sh`.
- `dcb5a389e2d4` — Hermes Mi v1.4.1 guardian, every 5m, local, `jarvis_mi_guardian.sh`.
- `4d7fbee50ff9` — Hermes Mi v1.4.1 healthcheck, every 120m, local, `jarvis_mi_healthcheck.sh`.
- `aded3c6554f3` — Hermes Mi v1.4.1 fill sync, every 10m, local, `jarvis_mi_sync_fills.sh`.
- `65b8d9feb0b3` — Hermes Mi v1.4.1 daily maincoin brief, 21:00 UTC+8, delivered to Feishu, `jarvis_mi_daily_review.sh`.
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
