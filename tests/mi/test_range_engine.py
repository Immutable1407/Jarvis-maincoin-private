import unittest
from types import SimpleNamespace

from jarvis_mi.range_engine import LimitedRangeSurviveEngine
from jarvis_mi.signal_score import Signal


def range_candles(price=101):
    return [{"o": 100, "h": 110, "l": 100, "c": price}] * 50


class TestRangeEngine(unittest.TestCase):
    def test_range_only_at_boundaries_high_quality(self):
        structure = SimpleNamespace(structure_regime="chop", range_quality_score=80)
        sig = Signal("BTC-USDT-SWAP", "long", 70, [], 101, 99, 1.6, "range_swing")
        d = LimitedRangeSurviveEngine().evaluate(sig, structure, range_candles(101))
        self.assertTrue(d.allow)
        self.assertEqual(d.boundary, "lower")

    def test_middle_range_blocks(self):
        structure = SimpleNamespace(structure_regime="chop", range_quality_score=80)
        sig = Signal("BTC-USDT-SWAP", "long", 70, [], 105, 99, 1.6, "range_swing")
        d = LimitedRangeSurviveEngine().evaluate(sig, structure, range_candles(105))
        self.assertFalse(d.allow)

    def test_low_quality_or_crash_blocks(self):
        sig = Signal("BTC-USDT-SWAP", "long", 70, [], 101, 99, 1.6, "range_swing")
        low = SimpleNamespace(structure_regime="chop", range_quality_score=50)
        self.assertFalse(LimitedRangeSurviveEngine().evaluate(sig, low, range_candles(101)).allow)
        high = SimpleNamespace(structure_regime="chop", range_quality_score=80)
        self.assertFalse(LimitedRangeSurviveEngine().evaluate(sig, high, range_candles(101), crash_or_squeeze=True).allow)


if __name__ == "__main__":
    unittest.main()
