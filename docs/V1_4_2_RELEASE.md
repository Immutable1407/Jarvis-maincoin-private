# Hermes Mi v1.4.2 Release Notes

## Summary

**v1.4.2 is an attribution-only upgrade.** No trading behavior, thresholds, sizing, leverage, lane scoring, guardian logic, or allowed instruments were changed. The objective is to make profit/loss attribution clear enough for GPT-5.5/Sir to decide whether existing lanes should be kept, tightened, or expanded.

## Changes from v1.4.1

### What changed
- **Version metadata:** `system_version = "v1.4.2-attribution-enhancement"`, `strategy_tag = "mi_v1_4_2_attribution_enhancement"`.
- **New module `jarvis_mi/attribution.py`:** Pure helpers for lifecycle and attribution keys. Includes `fill_key`, `parse_okx_ts_to_bjt_day`, `infer_fill_role`, `attribution_group_key`, and `summarize_attribution` for lane-level PnL reporting.
- **Enhanced fill enrichment:** `enrich_fill_with_decision_attribution()` now persists strategy_tag, strategy_lane, near_miss_pass, expected_net_pct, expected_tp1_net_pct, score, fill_role, attribution_group_key, and context fields. Matching prefers exact clOrdId/ordId then falls back to instId+side. Unknown fills get `fill_role="unknown"` and `attribution_warning="no_matching_decision"` instead of being silently unannotated.
- **Upgraded daily brief:** Adds 5 new sections: 归因总览, Lane贡献, Near-miss质量, 退出归因, 需要观察.
- **New audit script:** `scripts/mi/mi_attribution_audit.py` — read-only, inspects attribution without touching live orders. Supports `--day` and `--json` flags.

### What did NOT change
- Trading thresholds: `lane_min_expected_net_profit_pct`, `near_miss_profit_gate_ratio`, etc.
- Sizing, leverage, margin caps.
- Lane scoring logic.
- Guardian stop logic (local_stop, breakeven, trailing, partial TP).
- Allowed instruments: BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP, BNB-USDT-SWAP.
- Fill dedupe keys and seen-state persistence.
- `active_max_positions`, `enable_second_position`, `allow_mixed_direction_portfolio`.
- Account isolation: `HERMES_MI_OKX_*` only, UID `845800098641991226`.

## Verification

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_healthcheck.py
python3 scripts/mi/mi_attribution_audit.py --day $(TZ=Asia/Shanghai date +%F)
```

## New files
- `jarvis_mi/attribution.py` — attribution schema, helpers, summarizer
- `scripts/mi/mi_attribution_audit.py` — post-run audit command
- `tests/mi/test_v1_4_2_attribution.py` — unit tests for attribution layer
- `docs/V1_4_2_RELEASE.md` — this file

## Modified files
- `jarvis_mi/__init__.py` — version bump to 1.4.2
- `jarvis_mi/config_mi.py` — version/tag update
- `jarvis_mi/fills.py` — extended fill enrichment
- `jarvis_mi/performance.py` — upgraded daily_brief
- `docs/HERMES_MI_ARCHITECTURE.md` — updated to v1.4.2
- `docs/RUNBOOK.md` — updated with attribution audit command
- `AGENTS.md` — updated with v1.4.2 status

## Implementation
This release was implemented by DeepSeek v4 Pro following `docs/V1_4_2_ATTRIBUTION_PLAN_DEEPSEEK.md` mechanically, task-by-task.
