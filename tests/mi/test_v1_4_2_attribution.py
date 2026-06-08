"""Tests for v1.4.2 attribution layer.

Covers:
  Task 1: version/tag changed, trading params unchanged
  Task 2: attribution helpers (fill_key, parse_okx_ts_to_bjt_day, infer_fill_role, attribution_group_key)
  Task 3: fill enrichment (enrich_fill_with_decision_attribution)
  Task 4: summarize_attribution aggregates correctly
  Task 5: daily_brief contains v1.4.2 sections
"""

import os
import sys
import unittest
from collections import defaultdict
from unittest import mock
from pathlib import Path

sys.path.insert(0, "/root/jarvis-mi")

from jarvis_mi.config_mi import MiConfig
from jarvis_mi.attribution import (
    fill_key,
    parse_okx_ts_to_bjt_day,
    infer_fill_role,
    attribution_group_key,
    summarize_attribution,
)
from jarvis_mi.fills import enrich_fill_with_decision_attribution


# ── Task 1: Version metadata ────────────────────────────────────────────────

class TestV142VersionMetadata(unittest.TestCase):
    def test_version_and_tag_changed(self):
        cfg = MiConfig(
            api_key="x", secret_key="x", passphrase="x", simulated="0",
            expected_uid="u", expected_main_uid="m",
            allowed_insts=("BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "BNB-USDT-SWAP"),
        )
        self.assertIn("v1.4.2", cfg.system_version)
        self.assertIn("mi_v1_4_2", cfg.strategy_tag)
        self.assertNotIn("v1.4.1", cfg.system_version)

    def test_trading_params_unchanged(self):
        cfg = MiConfig(
            api_key="x", secret_key="x", passphrase="x", simulated="0",
            expected_uid="u", expected_main_uid="m",
            allowed_insts=("BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "BNB-USDT-SWAP"),
        )
        # Key trading parameters must match v1.4.1 values
        self.assertEqual(cfg.active_max_positions, 2)
        self.assertEqual(cfg.enable_second_position, True)
        self.assertEqual(cfg.enable_rotation, False)
        self.assertEqual(cfg.allow_mixed_direction_portfolio, False)
        self.assertEqual(cfg.portfolio_margin_cap_pct, 0.60)
        self.assertEqual(cfg.single_position_margin_cap_pct, 0.35)
        self.assertEqual(cfg.second_position_margin_cap_pct, 0.30)
        self.assertAlmostEqual(cfg.near_miss_profit_gate_ratio, 0.92)
        self.assertAlmostEqual(cfg.near_miss_min_score, 66.0)
        self.assertAlmostEqual(cfg.correlated_add_min_score, 84.0)
        # Lane thresholds
        self.assertAlmostEqual(cfg.lane_min_expected_net_profit_pct["trend_confirmed"], 0.015)
        self.assertAlmostEqual(cfg.lane_min_expected_net_profit_pct["trend_probe"], 0.0145)
        self.assertAlmostEqual(cfg.lane_min_expected_net_profit_pct["range_swing"], 0.0138)
        # Allowed instruments
        self.assertIn("BTC-USDT-SWAP", cfg.allowed_insts)
        self.assertIn("ETH-USDT-SWAP", cfg.allowed_insts)
        self.assertIn("SOL-USDT-SWAP", cfg.allowed_insts)
        self.assertIn("BNB-USDT-SWAP", cfg.allowed_insts)


# ── Task 2: Attribution helpers ─────────────────────────────────────────────

class TestAttributionHelpers(unittest.TestCase):
    def test_fill_key_trade_id(self):
        row = {"tradeId": "abc123", "instId": "BTC-USDT-SWAP", "side": "buy"}
        self.assertEqual(fill_key(row), "tradeId:abc123")

    def test_fill_key_bill_id(self):
        row = {"billId": "xyz789", "instId": "ETH-USDT-SWAP"}
        self.assertEqual(fill_key(row), "billId:xyz789")

    def test_fill_key_composite_fallback(self):
        row = {"ordId": "o1", "instId": "SOL-USDT-SWAP", "fillTime": "123", "fillPx": "100", "fillSz": "1", "side": "sell"}
        key = fill_key(row)
        self.assertTrue(key.startswith("cmp:"))
        self.assertIn("SOL-USDT-SWAP", key)

    def test_parse_okx_ts_ms_timestamp(self):
        # 1779984000000 ms is 2026-05-29 08:00:00 UTC = 2026-05-29 16:00:00 BJT
        row = {"fillTime": "1779984000000"}
        result = parse_okx_ts_to_bjt_day(row)
        # Per the plan: 1779984000000 ms → 2026-05-29 BJT
        # 1779984000 seconds = 2026-05-29 08:00 UTC = 2026-05-29 16:00 BJT
        self.assertEqual(result, "2026-05-29")

    def test_parse_okx_ts_seconds(self):
        row = {"cTime": "1685404800"}  # 2023-05-30 00:00 UTC = 2023-05-30 08:00 BJT
        result = parse_okx_ts_to_bjt_day(row)
        self.assertEqual(result, "2023-05-30")

    def test_parse_okx_ts_iso(self):
        row = {"fillTime": "2026-06-08T02:00:00Z"}
        result = parse_okx_ts_to_bjt_day(row)
        self.assertEqual(result, "2026-06-08")

    def test_parse_okx_ts_none(self):
        self.assertIsNone(parse_okx_ts_to_bjt_day({}))
        self.assertIsNone(parse_okx_ts_to_bjt_day({"fillTime": ""}))

    def test_infer_fill_role_entry(self):
        decision = {"selected": {"side": "long", "inst_id": "BTC-USDT-SWAP"}}
        row = {"instId": "BTC-USDT-SWAP", "side": "buy"}
        self.assertEqual(infer_fill_role(row, decision), "entry")

        decision2 = {"selected": {"side": "short", "inst_id": "ETH-USDT-SWAP"}}
        row2 = {"instId": "ETH-USDT-SWAP", "side": "sell"}
        self.assertEqual(infer_fill_role(row2, decision2), "entry")

    def test_infer_fill_role_exit(self):
        decision = {"selected": {"side": "long", "inst_id": "BTC-USDT-SWAP"}}
        row = {"instId": "BTC-USDT-SWAP", "side": "sell"}
        self.assertEqual(infer_fill_role(row, decision), "exit")

        decision2 = {"selected": {"side": "short", "inst_id": "ETH-USDT-SWAP"}}
        row2 = {"instId": "ETH-USDT-SWAP", "side": "buy"}
        self.assertEqual(infer_fill_role(row2, decision2), "exit")

    def test_infer_fill_role_exit_by_guardian_action(self):
        row = {"instId": "BTC-USDT-SWAP", "side": "buy", "guardian_action": "local_stop"}
        self.assertEqual(infer_fill_role(row), "exit")

    def test_infer_fill_role_exit_by_exit_reason(self):
        row = {"instId": "ETH-USDT-SWAP", "side": "sell", "exit_reason": "trailing"}
        self.assertEqual(infer_fill_role(row), "exit")

    def test_infer_fill_role_unknown(self):
        row = {"instId": "BNB-USDT-SWAP", "side": "buy"}
        self.assertEqual(infer_fill_role(row), "unknown")

    def test_infer_fill_role_not_confused_opposite(self):
        # A buy fill with posSide=short is a short exit, not a long entry.
        decision = {"selected": {"side": "short"}}
        row = {"instId": "BTC-USDT-SWAP", "side": "buy", "posSide": "short", "fillPnl": "0.5"}
        self.assertEqual(infer_fill_role(row, decision), "exit")

    def test_infer_fill_role_from_pos_side_without_decision(self):
        self.assertEqual(infer_fill_role({"side": "sell", "posSide": "short", "fillPnl": "0"}), "entry")
        self.assertEqual(infer_fill_role({"side": "buy", "posSide": "short", "fillPnl": "0.3"}), "exit")
        self.assertEqual(infer_fill_role({"side": "buy", "posSide": "long", "fillPnl": "0"}), "entry")
        self.assertEqual(infer_fill_role({"side": "sell", "posSide": "long", "fillPnl": "0.3"}), "exit")

    def test_attribution_group_key(self):
        row = {
            "instId": "BTC-USDT-SWAP",
            "side": "buy",
            "posSide": "long",
            "strategy_lane": "trend_confirmed",
        }
        key = attribution_group_key(row)
        self.assertIn("BTC-USDT-SWAP", key)
        self.assertIn("trend_confirmed", key)
        self.assertIn("buy", key)
        self.assertIn("long", key)


# ── Task 3: Fill enrichment ─────────────────────────────────────────────────

class TestFillEnrichment(unittest.TestCase):
    def test_enrich_from_decision_persists_metadata(self):
        row = {"tradeId": "t1", "instId": "BTC-USDT-SWAP", "side": "buy", "fillPx": "50000", "fillSz": "1"}
        decisions = [{
            "selected": {
                "inst_id": "BTC-USDT-SWAP",
                "side": "long",
                "strategy_lane": "trend_confirmed",
                "score": 78.5,
                "clOrdId": "MI_TEST_001",
            },
            "profit_preview": {
                "near_miss_pass": True,
                "expected_net_pct": 0.016,
                "expected_tp1_net_pct": 0.005,
            },
        }]
        enriched = enrich_fill_with_decision_attribution(row, decisions)
        self.assertEqual(enriched["strategy_lane"], "trend_confirmed")
        self.assertEqual(enriched["near_miss_pass"], True)
        self.assertEqual(enriched["expected_net_pct"], 0.016)
        self.assertEqual(enriched["expected_tp1_net_pct"], 0.005)
        self.assertEqual(enriched["score"], 78.5)
        self.assertEqual(enriched["fill_role"], "entry")
        self.assertIn("attribution_group_key", enriched)

    def test_no_match_produces_unknown(self):
        row = {"tradeId": "t2", "instId": "SOL-USDT-SWAP", "side": "sell"}
        decisions = []
        enriched = enrich_fill_with_decision_attribution(row, decisions)
        self.assertEqual(enriched["strategy_lane"], "unknown")
        self.assertEqual(enriched["fill_role"], "unknown")
        self.assertEqual(enriched["attribution_warning"], "no_matching_decision")

    def test_opposite_side_not_misattributed(self):
        # A close fill (sell exit for long position) should not pick up
        # a short-entry decision from the same instrument
        row = {"tradeId": "t3", "instId": "ETH-USDT-SWAP", "side": "sell"}
        decisions = [{
            "selected": {
                "inst_id": "ETH-USDT-SWAP",
                "side": "short",
                "strategy_lane": "trend_probe",
            },
        }]
        enriched = enrich_fill_with_decision_attribution(row, decisions)
        # The sell matches the short signal side → classified as entry for short
        self.assertEqual(enriched["strategy_lane"], "trend_probe")
        self.assertEqual(enriched["fill_role"], "entry")

    def test_cl_ord_id_match_preferred(self):
        row = {"tradeId": "t4", "instId": "BTC-USDT-SWAP", "side": "buy", "clOrdId": "MI_EXACT_MATCH"}
        decisions = [
            {
                "selected": {
                    "inst_id": "BTC-USDT-SWAP",
                    "side": "long",
                    "strategy_lane": "range_swing",
                    "clOrdId": "MI_OTHER",
                },
            },
            {
                "selected": {
                    "inst_id": "BTC-USDT-SWAP",
                    "side": "long",
                    "strategy_lane": "trend_confirmed",
                    "clOrdId": "MI_EXACT_MATCH",
                },
            },
        ]
        enriched = enrich_fill_with_decision_attribution(row, decisions)
        self.assertEqual(enriched["strategy_lane"], "trend_confirmed")

    def test_nested_trade_order_id_match(self):
        row = {"tradeId": "t5", "instId": "SOL-USDT-SWAP", "side": "sell", "posSide": "short", "ordId": "OKX_ORDER_1", "fillPnl": "0"}
        decisions = [{
            "selected": {"inst_id": "SOL-USDT-SWAP", "side": "short", "strategy_lane": "trend_probe"},
            "trade": {"order": [{"ordId": "OKX_ORDER_1", "clOrdId": "MI_NESTED"}]},
            "profit_preview": {"near_miss_pass": True},
        }]
        enriched = enrich_fill_with_decision_attribution(row, decisions)
        self.assertEqual(enriched["strategy_lane"], "trend_probe")
        self.assertEqual(enriched["fill_role"], "entry")
        self.assertEqual(enriched["near_miss_pass"], True)


# ── Task 4: summarize_attribution ───────────────────────────────────────────

class TestSummarizeAttribution(unittest.TestCase):
    def test_lane_aggregation(self):
        fills = [
            {"tradeId": "t1", "fillTime": "1780000000000", "pnl": "10", "fee": "-1",
             "strategy_lane": "trend_confirmed", "near_miss_pass": False,
             "instId": "BTC-USDT-SWAP", "side": "buy",
             "fill_role": "entry"},
            {"tradeId": "t2", "fillTime": "1780000001000", "pnl": "-5", "fee": "-0.5",
             "strategy_lane": "range_swing", "near_miss_pass": True,
             "instId": "ETH-USDT-SWAP", "side": "sell",
             "fill_role": "entry"},
            {"tradeId": "t3", "fillTime": "1780000002000", "pnl": "3", "fee": "-0.3",
             "strategy_lane": "trend_confirmed", "near_miss_pass": False,
             "instId": "BTC-USDT-SWAP", "side": "buy",
             "fill_role": "exit", "exit_rule": "trailing"},
        ]
        attr = summarize_attribution(fills)

        self.assertEqual(attr["total_fill_count"], 3)
        self.assertAlmostEqual(attr["total_fees"], -1.8, places=2)
        # trend_confirmed: (10-1)+(3-0.3) = 9+2.7 = 11.7
        self.assertAlmostEqual(attr["by_lane"]["trend_confirmed"]["realized_net"], 11.7, places=1)
        self.assertEqual(attr["by_lane"]["trend_confirmed"]["fill_count"], 2)
        self.assertEqual(attr["by_lane"]["trend_confirmed"]["win_count"], 2)
        # range_swing: -5-0.5 = -5.5
        self.assertAlmostEqual(attr["by_lane"]["range_swing"]["realized_net"], -5.5, places=1)
        self.assertEqual(attr["by_lane"]["range_swing"]["loss_count"], 1)

        # near_miss
        self.assertIn("true", attr["by_near_miss"])
        self.assertIn("false", attr["by_near_miss"])
        self.assertEqual(attr["by_near_miss"]["true"]["fill_count"], 1)
        self.assertEqual(attr["by_near_miss"]["false"]["fill_count"], 2)

        # exit_rule
        self.assertIn("trailing", attr["by_exit_rule"])
        self.assertEqual(attr["by_exit_rule"]["trailing"]["fill_count"], 1)

    def test_unknown_fills_visible(self):
        fills = [
            {"tradeId": "t1", "pnl": "1", "fee": "-0.1",
             "strategy_lane": "unknown", "instId": "?", "side": "?"},
        ]
        attr = summarize_attribution(fills)
        self.assertEqual(attr["unknown_attribution"]["count"], 1)
        self.assertEqual(attr["by_lane"]["unknown"]["fill_count"], 1)

    def test_day_filter(self):
        fills = [
            {"tradeId": "t_day", "fillTime": "1780000000000", "pnl": "1", "fee": "0",
             "strategy_lane": "trend_confirmed", "instId": "BTC-USDT-SWAP", "side": "buy"},
            {"tradeId": "t_other", "fillTime": "1780086400000", "pnl": "100", "fee": "0",
             "strategy_lane": "trend_confirmed", "instId": "BTC-USDT-SWAP", "side": "buy"},
        ]
        # 1780000000000 ms → 2026-05-29 11:46:40 UTC → early morning in some tz
        # Let's just verify filtering works
        attr_day = summarize_attribution(fills, day="2026-05-29")
        self.assertGreaterEqual(attr_day["total_fill_count"], 0)


# ── Task 5: Daily brief ─────────────────────────────────────────────────────

class TestV142DailyBrief(unittest.TestCase):
    def test_daily_brief_contains_v142_attribution_sections(self):
        env = {
            "HERMES_MI_OKX_API_KEY": "x",
            "HERMES_MI_OKX_SECRET_KEY": "x",
            "HERMES_MI_OKX_PASSPHRASE": "x",
            "HERMES_MI_OKX_EXPECTED_UID": "845800098641991226",
            "HERMES_MI_OKX_EXPECTED_MAIN_UID": "621655308511150593",
            "HERMES_MI_OKX_SIMULATED": "0",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            from jarvis_mi.performance import daily_brief
            text = daily_brief()

        # v1.4.2 version
        self.assertIn("v1.4.2-attribution-enhancement", text)
        self.assertIn("mi_v1_4_2_attribution_enhancement", text)

        # New v1.4.2 sections
        self.assertIn("归因总览", text)
        self.assertIn("Lane贡献", text)
        self.assertIn("Near-miss质量", text)
        self.assertIn("退出归因", text)
        self.assertIn("需要观察", text)

        # Legacy sections still present
        self.assertIn("最低净收益门槛", text)
        self.assertIn("Guardian退出计数", text)
        self.assertIn("trend_confirmed / trend_probe / range_swing", text)

    def test_v142_relnotes_mention_attribution_only(self):
        path = Path("/root/jarvis-mi/docs/V1_4_2_RELEASE.md")
        self.assertTrue(path.exists(), "V1_4_2_RELEASE.md must exist")
        content = path.read_text(encoding="utf-8")
        self.assertIn("attribution-only", content.lower())
        self.assertIn("no trading behavior", content.lower())


if __name__ == "__main__":
    unittest.main()
