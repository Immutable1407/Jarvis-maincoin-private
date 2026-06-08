# Hermes Mi v1.4.2 Attribution Enhancement Plan

> **For DeepSeek v4 pro:** Implement this plan mechanically, task-by-task. Do not explore new strategy edges. The current maincoin strategy state is good; the upgrade objective is to make profit/loss attribution clear enough for GPT-5.5/Sir to decide later whether existing lanes should be kept, tightened, or expanded.

**Goal:** Upgrade Hermes Mi from v1.4.1 to v1.4.2 by adding robust PnL attribution, exit attribution, and board-level reporting without changing entry/exit strategy behavior.

**Architecture:** Keep the hot path unchanged except for metadata persistence. Add a cold-path attribution layer that joins decisions, entries, fills, positions, and guardian exits by `instId + side + ordId/clOrdId + lifecycle window`. Reports should answer: which lane made money, which gate prevented losses, which exit rule captured/returned profit, and whether near-miss / second-position decisions are genuinely positive.

**Tech Stack:** Python stdlib, existing OKX client/ledgers, `unittest`, existing `/root/jarvis-mi` package.

---

## Non-negotiables

- Do **not** change thresholds, sizing, leverage, lane scoring, guardian stop logic, or allowed instruments in this release.
- Do **not** add LLM or external API calls to hot path.
- Metadata writes must fail loud enough for debugging, but must not block guardian risk protection.
- All runtime trading data stays under `data/` and `reports/`; do not commit secrets or ledgers.
- Maintain account isolation: only `HERMES_MI_OKX_*` credentials, only UID `845800098641991226` / main UID `621655308511150593`.

---

## Current baseline

- Live version: `v1.4.1-entry-report-fail-loud-hotfix`.
- Strategy tag: `mi_v1_4_1_entry_report_fail_loud_hotfix`.
- Active lanes: `trend_confirmed`, `trend_probe`, `range_swing`.
- User decision: strategy behavior is working; next upgrade focuses on attribution, not further strategy exploration.

---

## Task 1: Add explicit version metadata for v1.4.2

**Objective:** Create a visible version boundary for attribution-only changes.

**Files:**
- Modify: `jarvis_mi/config_mi.py`
- Test: `tests/mi/test_v1_4_2_attribution.py`

**Implementation:**

- Set:
  - `system_version = "v1.4.2-attribution-enhancement"`
  - `strategy_tag = "mi_v1_4_2_attribution_enhancement"`
- Keep every trading parameter identical to v1.4.1.

**Test:**

- Assert version/tag changed.
- Assert key trading params remain unchanged: `allowed_insts`, `active_max_positions`, lane thresholds, near-miss ratio, correlated add score, margin caps, mixed-direction block.

**Verification command:**

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m unittest tests.mi.test_v1_4_2_attribution -v
```

---

## Task 2: Define attribution record schema

**Objective:** Create reusable pure helpers for lifecycle and attribution keys.

**Files:**
- Create: `jarvis_mi/attribution.py`
- Test: `tests/mi/test_v1_4_2_attribution.py`

**Schema fields:**

- Identity: `instId`, `side`, `posSide`, `ordId`, `clOrdId`, `tradeId`, `fill_sync_key`.
- Strategy: `strategy_tag`, `strategy_lane`, `near_miss_pass`, `score`, `expected_net_pct`, `expected_tp1_net_pct`.
- Context: `market_regime`, `resonance_adjustment`, `portfolio_position_count`, `is_second_position`, `same_direction_group`.
- Entry/exit role: `fill_role = entry|exit|unknown`, `exit_reason`, `guardian_action`, `exit_rule = local_stop|breakeven|trailing|partial_tp|tp2_mfe|manual|unknown`.
- Economics: `fillPx`, `fillSz`, `fee`, `fillPnl`, `realized_net`, `r_estimate`.
- Time: raw OKX `fillTime/cTime`, parsed BJT day.

**Helpers:**

- `fill_key(row) -> str`
- `parse_okx_ts_to_bjt_day(row) -> str | None`
- `infer_fill_role(row, matching_decision=None, open_position_snapshot=None) -> str`
- `attribution_group_key(row) -> str`

**Tests:**

- Numeric ms timestamp and ISO timestamp both parse correctly.
- OKX negative fee contributes negative PnL in realized-net math but positive cost in fee-cost summaries.
- Buy entry / sell exit and sell entry / buy exit are not confused.

---

## Task 3: Improve fill enrichment without weakening dedupe

**Objective:** Persist enough metadata on each fill to make reports trustworthy.

**Files:**
- Modify: `jarvis_mi/fills.py`
- Test: `tests/mi/test_v1_4_2_attribution.py`

**Implementation:**

- Keep `_fill_key()` and `_load_seen()` behavior unchanged.
- Extend `enrich_fill_with_decision_attribution()` to persist:
  - `strategy_tag`
  - `strategy_lane`
  - `near_miss_pass`
  - `expected_net_pct`
  - `expected_tp1_net_pct`
  - `score` / `total_score` if available
  - `fill_role` best effort
  - `attribution_group_key`
- Matching must prefer exact `clOrdId/ordId` when present, then fall back to latest matching `instId + side` decision.
- If no match exists, write `fill_role="unknown"` and `attribution_warning="no_matching_decision"`; do not fake lane.

**Regression tests:**

- A close fill with opposite side must not be attributed as a new entry lane unless lifecycle/order mapping says so.
- Missing decision does not crash sync and produces warning metadata.
- Dedupe count remains stable when enrichment changes.

---

## Task 4: Build lane-level PnL attribution summary

**Objective:** Report realized PnL by lane, near-miss status, symbol, side, and exit reason.

**Files:**
- Modify/Create: `jarvis_mi/performance.py` or `jarvis_mi/attribution.py`
- Test: `tests/mi/test_v1_4_2_attribution.py`

**Function:**

```python
def summarize_attribution(fills: list[dict], decisions: list[dict], guardian: list[dict], *, day: str | None = None) -> dict:
    ...
```

**Output groups:**

- `by_lane`: counts, realized_net, fees, avg_net_per_fill, win/loss fill counts.
- `by_near_miss`: near-miss vs normal pass realized contribution.
- `by_symbol_side`: realized contribution and fill count.
- `by_exit_rule`: local_stop / breakeven / trailing / partial_tp / unknown.
- `unknown_attribution`: count and sample keys.

**Tests:**

- One profitable `trend_confirmed` lifecycle and one losing `range_swing` lifecycle aggregate correctly.
- Near-miss fill appears in `by_near_miss.true`.
- Unknown fills are visible instead of silently dropped.

---

## Task 5: Upgrade daily board brief

**Objective:** Make the daily report explain why the strategy made/lost money.

**Files:**
- Modify: `jarvis_mi/performance.py`
- Test: `tests/mi/test_performance_report.py` and/or `tests/mi/test_v1_4_2_attribution.py`

**Report additions:**

Add concise sections:

- `归因总览`: realized net, fees, fill count, unknown attribution count.
- `Lane贡献`: lane → realized_net / fills / near_miss count.
- `Near-miss质量`: near-miss contribution vs normal contribution.
- `退出归因`: Guardian exit rule counts and realized contribution where inferable.
- `需要观察`: e.g. unknown attribution too high, one lane has fills but negative net, second-position sample too small.

**Acceptance:**

- Report remains Telegram/Feishu friendly: bullet list, no markdown tables.
- Existing summary lines stay intact unless directly replaced by richer equivalent.

---

## Task 6: Add post-run attribution audit command

**Objective:** Give GPT-5.5/Sir a stable command to inspect attribution without touching live orders.

**Files:**
- Create: `scripts/mi/mi_attribution_audit.py`
- Test: optionally invoke from unit test via temp ledgers, or keep as smoke script.

**Behavior:**

- Read `data/mi/ledgers/decisions.jsonl`, `fills.jsonl`, `guardian.jsonl`.
- Print JSON + human-readable bullet summary.
- Optional `--day YYYY-MM-DD`.
- Optional `--json`.

**Verification command:**

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 scripts/mi/mi_attribution_audit.py --day $(TZ=Asia/Shanghai date +%F)
```

---

## Task 7: Documentation and release note

**Objective:** Document that v1.4.2 is attribution-only.

**Files:**
- Create: `docs/V1_4_2_RELEASE.md`
- Modify: `docs/HERMES_MI_ARCHITECTURE.md`
- Modify: `docs/RUNBOOK.md`
- Modify: `AGENTS.md`

**Docs must say:**

- v1.4.2 changes reporting/attribution, not trading logic.
- New script: `scripts/mi/mi_attribution_audit.py`.
- DeepSeek implementation must run full tests and account-isolation/health checks before live cron tag update.

---

## Final verification

Run exactly:

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_healthcheck.py
python3 scripts/mi/mi_attribution_audit.py --day $(TZ=Asia/Shanghai date +%F)
```

If the implementation changes live cron labels/version, also list crons and verify delivery remains summary-only.

---

## GPT-5.5 review checklist after DeepSeek implementation

- Trading thresholds and allowed instruments unchanged.
- Fills remain deduped by existing keys.
- Entry vs exit fills are not misclassified by side alone.
- Unknown attribution is visible and bounded.
- Daily brief answers: lane PnL, near-miss PnL, exit-rule PnL, top blockers.
- No live-order script was run unintentionally during implementation.
