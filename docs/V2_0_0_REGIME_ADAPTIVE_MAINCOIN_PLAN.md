# Hermes Mi v2.0.0 Regime-Adaptive Maincoin System Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task after Sir approves execution. Keep LLMs out of the hot path. Use `/root/jarvis-mi` only. Never touch secrets or runtime account data in Git.

**Goal:** First ship v2.0.0 as the complete new foundation, then run fixed two-day debug/iteration cycles from v2.1.0 through v2.9.0 until the system reaches stable state.

**Architecture:** v2.0.0 is not a gradual foundation build. It is the foundation replacement: `MarketStructureClassifier -> TrendWearGovernor -> ModeRouter -> Mode-specific signal gates -> SecondConfirmationGate -> RiskLadderV2 -> PortfolioGuard -> Execution/Guardian -> Attribution/Feedback`. After v2.0.0, each two-day version is a calibration, bug-fix, or threshold-hardening release based on live/shadow evidence.

**Tech Stack:** Python stdlib, existing `jarvis_mi` modules, OKX REST wrapper already present in project, existing unittest suite under `tests/mi`, existing scripts under `scripts/mi`, daily brief/reporting pipeline.

---

## Corrected rollout philosophy

Sir corrected the earlier staged plan: the system should not spend multiple releases gradually constructing the foundation. The correct process is:

```text
1. Build and ship the full v2.0.0 foundation first.
2. Run the new system under guarded risk.
3. Iterate/debug every two days: v2.1.0 -> v2.9.0.
4. After at least 18 days of v2.x evidence, declare stable state only if acceptance criteria are met.
```

Reason: if the goal is regime-adaptive trading, partial foundation releases can create misleading behavior. For example, a classifier without router, or a router without wear governor, is not the real v2 system. The first live/guarded version should contain the full architecture so feedback is gathered on the actual system, not a transitional hybrid.

---

## Product thesis

v1.x failure mode: `trend_confirmed` was treated as sufficient evidence for a trend environment. In chop/transition markets, this causes repeated false-breakout and no-MFE wear.

v2.0.0 thesis:

```text
TREND        -> Hunter / Trend Engine: normal risk only after second confirmation.
TRANSITION   -> Probe Engine: small probe only; promote to TREND only after confirmation.
CHOP         -> Range-Survive only if range quality is high; otherwise WAIT.
WAIT         -> no new entries; preserve capital.
```

Main profit source remains trend. Survival comes from refusing to run trend logic during non-trend regimes.

---

## Version timeline: foundation first, then two-day debug cycles

### Day 0-2 — v2.0.0 Foundation Release

**Objective:** Implement the full regime-adaptive foundation in one coherent release, with guarded-risk defaults.

**Modules included at launch:**

1. `MarketStructureClassifier`
2. `ModeRouter`
3. `SecondConfirmationGate`
4. `TrendWearGovernor`
5. `RiskLadderV2`
6. `LimitedRangeSurviveEngine`
7. `CounterfactualEvaluator`
8. `Mode/Lane/Exit Attribution v2`
9. `Daily Report v2`
10. `Replay/diagnostic hooks`

**Files likely created:**

- `jarvis_mi/market_structure.py`
- `jarvis_mi/mode_router.py`
- `jarvis_mi/confirmation.py`
- `jarvis_mi/trend_wear.py`
- `jarvis_mi/range_engine.py`
- `jarvis_mi/risk_ladder_v2.py`
- `jarvis_mi/counterfactual.py`
- `tests/mi/test_market_structure.py`
- `tests/mi/test_mode_router.py`
- `tests/mi/test_confirmation_gate.py`
- `tests/mi/test_trend_wear.py`
- `tests/mi/test_range_engine.py`
- `tests/mi/test_risk_ladder_v2.py`
- `tests/mi/test_counterfactual.py`
- `docs/V2_0_0_RELEASE.md`

**Files likely modified after inspection:**

- `jarvis_mi/signals.py`
- `jarvis_mi/risk.py`
- `jarvis_mi/attribution.py`
- `jarvis_mi/performance.py`
- `scripts/mi/mi_live_cycle.py`
- `scripts/mi/mi_daily_review.py`
- `docs/HERMES_MI_ARCHITECTURE.md`
- `docs/RUNBOOK.md`

**v2.0.0 guarded defaults:**

- TREND normal risk enabled only after second confirmation.
- TRANSITION is probe-only.
- CHOP defaults to WAIT unless range quality is high.
- RANGE live risk is capped at tiny/conservative level for first 48h.
- Drawdown/wear override can only reduce risk, never increase it.
- If classifier/router errors, fail closed to WAIT or safest no-entry path.

**Verification commands:**

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_sync_fills.py
python3 scripts/mi/mi_healthcheck.py
python3 scripts/mi/mi_attribution_audit.py
python3 scripts/mi/mi_daily_review.py
```

**Acceptance criteria:**

- Hot path includes full v2 architecture.
- No LLM in hot path.
- UID/whitelist/credential isolation unchanged.
- Guardian/fill-sync/healthcheck unchanged.
- Daily brief can explain current mode, risk tier, active cooldowns, and blocked trade counterfactuals.
- New system can run under guarded risk without partial-foundation ambiguity.

---

## v2.1.0 to v2.9.0: fixed two-day iteration cycle

Each cycle uses the same process:

```text
Day N morning/evening:
  1. Run fill sync.
  2. Rebuild BJT-day PnL from deduped fills.
  3. Review daily brief + snapshots + counterfactuals.
  4. Identify one primary failure mode.
  5. Patch only that failure mode.
  6. Run compile/unit/health/audit/daily-review checks.
  7. Update release notes.
```

No cycle may loosen risk after a losing or ambiguous two-day window. Risk expansion is allowed only after clear evidence and explicit Sir approval.

---

### Days 2-4 — v2.1.0 Classifier Calibration

**Objective:** Calibrate TREND/TRANSITION/CHOP/WAIT labels against first two days of v2 evidence.

**Focus questions:**

- Did classifier over-label chop as trend?
- Did classifier miss obvious trend continuation?
- Were WAIT periods truly no-edge?
- Did mode confidence match actual MFE/MAE?

**Allowed changes:**

- MA slope thresholds.
- Trend persistence score.
- False-breakout risk score.
- Range quality scoring.
- Reason-code clarity.

**Not allowed:**

- Raising leverage or max positions.
- Making CHOP more active without evidence.

---

### Days 4-6 — v2.2.0 Confirmation Gate Calibration

**Objective:** Tune second-confirmation rules so fake breakouts stay small but real trends are not completely missed.

**Focus questions:**

- Were blocked first-breakout trades mostly losers?
- Did any blocked trade become a large trend without a second-confirmation opportunity?
- Are N-bar and pullback rules too strict or too loose?

**Allowed changes:**

- Confirmation bar count.
- Breakout-zone tolerance.
- Early MFE threshold.
- BTC/ETH divergence threshold.

---

### Days 6-8 — v2.3.0 Trend Wear Governor Calibration

**Objective:** Ensure trend wear blocks repeated same-mode losses quickly enough without overreacting to normal trend probing.

**Focus questions:**

- Did no-MFE clusters trigger cooldown?
- Did same symbol/side losses repeat after cooldown should have applied?
- Did wear governor demote TREND to TRANSITION appropriately?

**Allowed changes:**

- No-MFE threshold.
- Cooldown duration.
- Same symbol/side failure count.
- Lane-level wear trigger.

---

### Days 8-10 — v2.4.0 Range-Survive Calibration

**Objective:** Validate whether high-quality range trading is actually useful, or whether CHOP should remain mostly WAIT.

**Focus questions:**

- Did range trades occur only at boundaries?
- Did fees eat range gross profit?
- Did any middle-range entries slip through?
- Did failed range trade trigger cooldown?

**Allowed changes:**

- Range quality threshold.
- Boundary proximity threshold.
- TP/time-stop rules.
- Range cooldown.

**Rule:** If range evidence is weak, tighten or disable range. Do not force activity.

---

### Days 10-12 — v2.5.0 Risk Ladder and Drawdown Override Calibration

**Objective:** Check whether mode-specific risk caps are correctly sized for the small account.

**Focus questions:**

- Is max loss per mode tolerable relative to equity?
- Are fees too large relative to expected edge?
- Did drawdown override trigger early enough?
- Did risk restore too quickly after losses?

**Allowed changes:**

- Mode leverage caps downward or cautiously upward only after profitable evidence.
- Max loss pct downward after wear.
- Drawdown override thresholds.
- Fee edge threshold.

---

### Days 12-14 — v2.6.0 Attribution and Report Reliability

**Objective:** Make reports board-grade and remove unknown attribution where possible.

**Focus questions:**

- Are exit reasons correctly mapped?
- Does daily report match deduped OKX fills after sync?
- Are mode/lane/symbol/side PnL sections actionable?
- Are counterfactuals readable?

**Allowed changes:**

- Exit attribution mapping.
- Fill enrichment.
- Daily brief sections.
- Audit script checks.

---

### Days 14-16 — v2.7.0 Replay and Counterfactual Hardening

**Objective:** Improve cold-path evaluation: what v2 blocked, what it missed, and whether that was correct.

**Focus questions:**

- Do blocked v1-style trades have later MFE/MAE tracked?
- Did WAIT avoid losses or miss edge?
- Are replay diagnostics sufficient for threshold updates?

**Allowed changes:**

- Snapshot schema.
- Counterfactual tracking.
- Replay scripts.
- Report summary of prevented trades.

---

### Days 16-18 — v2.8.0 Portfolio/Correlation Governance

**Objective:** Ensure the two-position system does not stack correlated false thesis risk.

**Focus questions:**

- Did BTC/ETH long + ETH/SOL/BNB long behave as one correlated bet?
- Did second position add real edge or just amplify same thesis?
- Did mixed direction block remain safe?

**Allowed changes:**

- Second-position permission thresholds.
- Correlation/crowding guard.
- BTC/ETH primary gate weights.
- SOL/BNB role as confirmation, not independent full-risk trigger.

---

### Days 18-20 — v2.9.0 Stability Candidate

**Objective:** Freeze the first stable v2.x configuration if evidence is acceptable.

**Stability criteria:**

- CHOP does not produce repeated trend losses.
- TRANSITION keeps fake-breakout losses small.
- TREND still allows meaningful attack after confirmation.
- Range either proves positive/low-wear or remains mostly disabled.
- Daily report explains behavior clearly.
- No hot-path exceptions.
- No UID/whitelist/risk invariant regression.

**Outputs:**

- `docs/V2_9_0_STABILITY_REVIEW.md`
- Decision: stable / continue v2.10+ iteration / rollback selected component.

---

## v2.0.0 module specifications

### 1. MarketStructureClassifier

Outputs:

- `structure_regime`: `trend | transition | chop | wait`
- `structure_confidence`: 0-100
- `trend_direction`: `long | short | both | none`
- `reason_codes`
- `range_quality_score`
- `trend_persistence_score`
- `false_breakout_risk_score`

Inputs:

- Existing market state.
- BTC/ETH/SOL/BNB candles.
- Returns alignment.
- MA slope / price-vs-MA persistence.
- Recent MA cross frequency.
- Range width and boundary clarity.
- ATR directionality.
- Wick/rejection proxy.
- Resonance output.

### 2. ModeRouter

Maps classifier + wear + drawdown to permissions:

- `allow_trend_confirmed_normal`
- `allow_trend_probe`
- `allow_range_swing`
- `allow_second_position`
- `max_leverage`
- `max_loss_pct`
- `risk_tier`
- `mode_reason_codes`

### 3. SecondConfirmationGate

Blocks first-breakout normal-risk entries in transition/chop.

Promotion conditions:

- Breakout persists for configured bars.
- Pullback does not invalidate structure.
- BTC/ETH no immediate divergence.
- Price does not quickly re-enter prior range.
- Early MFE / structural persistence passes.

### 4. TrendWearGovernor

Detects repeated trend wear:

- no-MFE trend entries;
- repeated same symbol/side stopouts;
- trend_confirmed daily loss;
- breakeven/local-stop clustering;
- false-breakout signature;
- consecutive losing days.

Actions:

- Level 1: normal -> reduced.
- Level 2: TREND -> TRANSITION.
- Level 3: no new trend entries until cooldown/next BJT day.

### 5. RiskLadderV2

```text
WAIT:
  new entries: disabled
  max_positions: 0

CHOP:
  default: WAIT
  allowed lane: range_survive only if high-quality range
  leverage: 3-5x
  max_loss_pct: 0.5%-1.0%
  max_positions: 1

TRANSITION:
  allowed lane: probe only
  leverage: 5-6x
  max_loss_pct: 1.0%-1.5%
  max_positions: 1
  no second position

TREND:
  allowed lanes: trend_confirmed, trend_probe
  leverage: 8-10x only after second confirmation
  max_loss_pct: 2.0%-3.0%
  max_positions: 2
```

Drawdown override lowers the mode risk one tier after daily loss or repeated lane wear.

### 6. LimitedRangeSurviveEngine

CHOP default is WAIT. Range is allowed only if:

- boundary clarity score >= threshold;
- price is near upper/lower boundary, not middle;
- fee-adjusted expected edge passes;
- stop distance is structurally valid;
- no recent range cooldown;
- BTC is not crash/squeeze.

A failed range trade triggers cooldown.

### 7. CounterfactualEvaluator

Daily answers:

- What would v1.x have traded that v2 blocked?
- Did blocked trades later show loss/no-MFE?
- What did v2 miss?
- Was WAIT correct?
- Did second confirmation reduce or merely delay edge?

---

## Reporting requirements

Daily brief must include:

1. Current regime/mode.
2. Mode confidence and reason codes.
3. Realized net PnL by BJT day after fill sync.
4. Mode PnL: TREND / TRANSITION / RANGE / WAIT.
5. Lane PnL: trend_confirmed / trend_probe / range_swing.
6. Wear diagnostics: no-MFE count, stopout count, cooldowns.
7. Counterfactuals: blocked v1 trades and their later MFE/MAE where available.
8. Active risk tier and whether drawdown override is active.
9. Next-day stance: continue / observe / guarded / patch / pause.

---

## Global safety invariants

- Only instruments: BTC/ETH/SOL/BNB USDT swaps.
- UID/mainUid guard unchanged.
- No mixed long/short portfolio unless explicitly approved later.
- Guardian never paused by strategy upgrade.
- Fill sync never paused by strategy upgrade.
- Healthcheck never paused by strategy upgrade.
- Runtime data and reports stay out of Git.
- No secrets in docs/tests.
- No LLM in hot path.

---

## Operating policy during v2.0.0 -> v2.9.0

- The first v2.0.0 release should run guarded, not aggressive.
- The system should not wait until v2.9.0 to contain all foundation modules; all foundation modules ship in v2.0.0.
- Every two days, patch based on observed failure mode.
- If a component causes ambiguous behavior, disable/tighten that component rather than loosening the entire system.
- Risk expansion requires positive evidence plus Sir approval.

---

## Open decisions for Sir

1. During v2.0.0 first 48h, should live-cycle allow guarded entries or pause all new entries while producing full decisions?
2. Range-Survive in v2.0.0: tiny-risk live from day one, or decision-only shadow for first 48h?
3. Tag strategy: tag v2.0.0 and every two-day minor release v2.1.0 ... v2.9.0, or tag only v2.0.0/v2.5.0/v2.9.0?

Jarvis recommendation:

- v2.0.0 should include all foundation modules immediately.
- First 48h should use guarded live or decision-only mode depending on Sir risk tolerance.
- Range-Survive should be shadow or tiny-risk only in first 48h.
- Tag every two-day minor release because v2.x is a structured stabilization campaign.
