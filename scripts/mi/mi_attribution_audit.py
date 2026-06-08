#!/usr/bin/env python3
"""Hermes Mi v1.4.2 Attribution Audit — read-only, no live orders.

Usage:
    python3 scripts/mi/mi_attribution_audit.py
    python3 scripts/mi/mi_attribution_audit.py --day 2026-06-08
    python3 scripts/mi/mi_attribution_audit.py --day 2026-06-08 --json

Reads data/mi/ledgers/decisions.jsonl, fills.jsonl, guardian.jsonl and prints:
  - JSON (if --json)
  - Human-readable bullet summary

Safe for GPT-5.5/Sir to inspect attribution without touching live orders.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from jarvis_mi.attribution import summarize_attribution
from jarvis_mi.config_mi import LEDGER_DIR
from jarvis_mi.performance import _read_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hermes Mi v1.4.2 Attribution Audit",
    )
    parser.add_argument(
        "--day",
        type=str,
        default=None,
        help="Filter by BJT day (YYYY-MM-DD). Default: all available data.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of human-readable bullet summary.",
    )
    args = parser.parse_args()

    fills = _read_jsonl("fills.jsonl")
    decisions = _read_jsonl("decisions.jsonl")
    guardian = _read_jsonl("guardian.jsonl")

    if not fills:
        print("No fill data found.", file=sys.stderr)
        sys.exit(0)

    attr = summarize_attribution(fills, decisions, guardian, day=args.day)

    if args.json:
        print(json.dumps(attr, ensure_ascii=False, indent=2, default=str))
        return

    # ── Human-readable bullet summary ──
    day_label = args.day or "全量"
    print(f"# Hermes Mi 归因审计 {day_label}")
    print()

    print("## 归因总览")
    print(f"- 已实现费后净额: {attr['total_realized_net']:.4f} USDT")
    print(f"- 手续费合计: {attr['total_fees']:.4f} USDT")
    print(f"- 去重成交数: {attr['total_fill_count']}")
    print(f"- 未知归因: {attr['unknown_attribution']['count']}")
    print()

    print("## Lane贡献")
    if attr["by_lane"]:
        for lane_name, ld in attr["by_lane"].items():
            print(
                f"- {lane_name}: net={ld['realized_net']:+.4f}  "
                f"fills={ld['fill_count']}  "
                f"win/loss={ld['win_count']}/{ld['loss_count']}  "
                f"avg={ld['avg_net_per_fill']:+.4f}  "
                f"fees={ld['fees']:.4f}"
            )
    else:
        print("- 无")
    print()

    print("## Near-miss质量")
    nm_false = attr["by_near_miss"].get("false", {})
    nm_true = attr["by_near_miss"].get("true", {})
    print(
        f"- near-miss: net={nm_true.get('realized_net', 0):+.4f}  "
        f"fills={nm_true.get('fill_count', 0)}"
    )
    print(
        f"- normal: net={nm_false.get('realized_net', 0):+.4f}  "
        f"fills={nm_false.get('fill_count', 0)}"
    )
    print()

    print("## Symbol/Side")
    if attr["by_symbol_side"]:
        for ss_key, sd in attr["by_symbol_side"].items():
            if sd["fill_count"] > 0:
                print(f"- {ss_key}: net={sd['realized_net']:+.4f}  fills={sd['fill_count']}")
    else:
        print("- 无")
    print()

    print("## 退出归因")
    if attr["by_exit_rule"]:
        for er, ed in attr["by_exit_rule"].items():
            if ed["fill_count"] > 0:
                print(f"- {er}: net={ed['realized_net']:+.4f}  fills={ed['fill_count']}")
    else:
        print("- 无退出归因数据")
    print()

    if attr["unknown_attribution"]["count"] > 0:
        print("## 未知归因样本")
        for key in attr["unknown_attribution"]["sample_keys"]:
            print(f"- {key}")
        print()


if __name__ == "__main__":
    main()
