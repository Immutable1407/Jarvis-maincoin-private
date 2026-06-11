import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis_mi.counterfactual import CounterfactualEvaluator
from jarvis_mi.signal_score import Signal


class TestCounterfactualEvaluator(unittest.TestCase):
    def test_records_safe_jsonl_under_temp_data_dir(self):
        with tempfile.TemporaryDirectory() as td:
            ce = CounterfactualEvaluator(Path(td))
            sig = Signal("BTC-USDT-SWAP", "long", 74, [], 100, 98, 1.5, "trend_confirmed")
            rec = ce.record_blocked(sig, "v2_confirmation_or_mode_block", mode=SimpleNamespace(mode="CHOP"), structure=SimpleNamespace(structure_regime="chop"))
            self.assertEqual(rec["inst_id"], "BTC-USDT-SWAP")
            ledger = Path(td) / "ledgers" / "counterfactuals.jsonl"
            self.assertTrue(ledger.exists())
            summary = ce.summarize()
            self.assertEqual(summary["blocked_total"], 1)
            self.assertEqual(summary["by_reason"]["v2_confirmation_or_mode_block"], 1)


if __name__ == "__main__":
    unittest.main()
