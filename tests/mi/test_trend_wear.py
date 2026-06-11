import json
import tempfile
import unittest
from pathlib import Path

from jarvis_mi.trend_wear import TrendWearGovernor


class TestTrendWearGovernor(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
