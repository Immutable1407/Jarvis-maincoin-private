import json
import tempfile
import unittest
from pathlib import Path

from jarvis_mi.trend_wear import TrendWearGovernor


class TestTrendWearGovernor(unittest.TestCase):
    def _evaluate_with_fills(self, rows, side="long"):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ledgers = root / "ledgers"
            state = root / "state"
            ledgers.mkdir()
            state.mkdir()
            (ledgers / "fills.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            return TrendWearGovernor(ledgers, state).evaluate("BTC-USDT-SWAP", side)

    def test_no_mfe_stopout_loss_cluster_raises_wear(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ledgers = root / "ledgers"; state = root / "state"
            ledgers.mkdir(); state.mkdir()
            rows = [
                {"selected": {"inst_id": "BTC-USDT-SWAP", "side": "long", "strategy_lane": "trend_confirmed", "reason": ["no_mfe_false_breakout"]}},
                {"selected": {"inst_id": "BTC-USDT-SWAP", "side": "long", "strategy_lane": "trend_confirmed", "reason": ["no_mfe"]}},
            ]
            (ledgers / "decisions.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            g = [{"actions": [{"instId": "BTC-USDT-SWAP", "reason": "local_stop_no_mfe"}]}]
            (ledgers / "guardian.jsonl").write_text("\n".join(json.dumps(r) for r in g), encoding="utf-8")
            st = TrendWearGovernor(ledgers, state).evaluate("BTC-USDT-SWAP", "long")
            self.assertGreaterEqual(st.wear_level, 2)
            self.assertIn("reduce_risk", st.actions)

    def test_missing_ledgers_safe_clear(self):
        with tempfile.TemporaryDirectory() as td:
            st = TrendWearGovernor(Path(td) / "ledgers", Path(td) / "state").evaluate()
            self.assertEqual(st.wear_level, 0)

    def test_trend_entry_fee_rows_do_not_increase_losses(self):
        rows = [
            {
                "instId": "BTC-USDT-SWAP",
                "side": "buy",
                "posSide": "long",
                "strategy_lane": "trend_confirmed",
                "fill_role": "entry",
                "fillPnl": "0",
                "fee": "-0.18",
            }
            for _ in range(6)
        ]
        st = self._evaluate_with_fills(rows, "long")
        self.assertEqual(st.loss_count, 0)
        self.assertEqual(st.wear_level, 0)
        self.assertNotIn("trend_loss_count_6", st.reason_codes)

    def test_trend_exit_loss_rows_are_counted(self):
        rows = [
            {
                "instId": "BTC-USDT-SWAP",
                "side": "sell",
                "posSide": "long",
                "strategy_lane": "trend_confirmed",
                "fill_role": "exit",
                "fillPnl": "-2.0",
                "fee": "-0.1",
            },
            {
                "instId": "BTC-USDT-SWAP",
                "side": "sell",
                "strategy_lane": "trend_confirmed",
                "order_role": "exit",
                "fillPnl": "-1.0",
                "fee": "-0.1",
            },
        ]
        st = self._evaluate_with_fills(rows, "long")
        self.assertEqual(st.loss_count, 2)
        self.assertIn("trend_loss_count_2", st.reason_codes)
        self.assertEqual(st.wear_level, 1)

    def test_legacy_fee_only_rows_without_role_are_ignored(self):
        rows = [
            {
                "instId": "BTC-USDT-SWAP",
                "side": "buy",
                "posSide": "long",
                "strategy_lane": "trend_confirmed",
                "fillPnl": "0",
                "fee": "-0.2",
            }
            for _ in range(5)
        ]
        st = self._evaluate_with_fills(rows, "long")
        self.assertEqual(st.loss_count, 0)
        self.assertEqual(st.wear_level, 0)

    def test_legacy_nonzero_realized_loss_without_role_is_counted(self):
        rows = [{
            "instId": "BTC-USDT-SWAP",
            "side": "long",
            "strategy_lane": "trend_confirmed",
            "fillPnl": "-0.5",
            "fee": "-0.02",
        }]
        st = self._evaluate_with_fills(rows, "long")
        self.assertEqual(st.loss_count, 1)


if __name__ == "__main__":
    unittest.main()
