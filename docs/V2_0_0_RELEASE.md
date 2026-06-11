# Hermes Mi v2.0.0 Release — Regime-Adaptive Maincoin Foundation

## Summary

v2.0.0 replaces the v1.x lane-only foundation with a deterministic regime-adaptive hot path:

`MarketStructureClassifier -> TrendWearGovernor -> ModeRouter -> Mode-specific gates -> SecondConfirmationGate -> RiskLadderV2 -> Portfolio/Correlation/Profit Guards -> Execution/Guardian -> Attribution/Feedback`

No LLM is used in the hot path. OKX account guard, UID/mainUid isolation, Hermes Mi credential prefix, whitelist checks, guardian, fill sync, and healthcheck remain preserved.

## Guarded defaults

- WAIT: no new entries.
- CHOP: trend entries blocked; range_swing only if high-quality range, boundary price, fee-adjusted edge, no crash/squeeze/cooldown.
- TRANSITION: probe-only; normal trend_confirmed blocked.
- TREND: trend_confirmed normal risk only after second confirmation; trend_probe remains reduced/probe.
- Trend wear and drawdown overrides can only reduce risk.
- Any v2 classifier/router/gate error fails closed to WAIT/no entry.

## New modules

- `jarvis_mi/market_structure.py`
- `jarvis_mi/trend_wear.py`
- `jarvis_mi/mode_router.py`
- `jarvis_mi/confirmation.py`
- `jarvis_mi/range_engine.py`
- `jarvis_mi/risk_ladder_v2.py`
- `jarvis_mi/counterfactual.py`

## Hot-path integration

`scripts/mi/mi_live_cycle.py` now computes v2 structure/wear/mode after market state and resonance, before candidate execution. Candidate handling applies:

1. mode/lane permission checks,
2. second-confirmation gate for `trend_confirmed`,
3. range-survive gate for `range_swing`,
4. RiskLadderV2 sizing caps,
5. existing portfolio, cooldown, profit, correlation, sizing, and execution path.

`execute_entry` remains the only live OKX order write point. This release was not verified by running `mi_live_cycle.py` because it can place live orders.

## Reporting

Daily brief includes v2 regime/mode, confidence/reasons, risk tier, wear diagnostics, counterfactual summary, and mode/lane PnL placeholders for future v2 fill enrichment.

## Verification

Required safe checks:

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
```

Do not run `scripts/mi/mi_live_cycle.py` as verification; it can place a live order.
