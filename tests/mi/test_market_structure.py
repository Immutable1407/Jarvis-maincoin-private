import unittest
from types import SimpleNamespace

from jarvis_mi.market_structure import MarketStructureClassifier, candle_value


def candles_trend(n=80, start=100.0, step=0.6):
    out = []
    for i in range(n):
        c = start + i * step
        out.append({"o": c - 0.2, "h": c + 0.5, "l": c - 0.5, "c": c})
    return out


def candles_chop(n=80, base=100.0):
    out = []
    for i in range(n):
        c = base + (1 if i % 2 else -1) * 1.6
        out.append({"o": base, "h": base + 2.0, "l": base - 2.0, "c": c})
    return out


class TestMarketStructureClassifier(unittest.TestCase):
    def test_robust_candle_access_okx_list_and_dict(self):
        self.assertEqual(candle_value([123, "1", "2", "0.5", "1.5"], "c"), 1.5)
        self.assertEqual(candle_value({"close": "2.5"}, "c"), 2.5)

    def test_trend_detected_with_confidence(self):
        c = candles_trend()
        res = MarketStructureClassifier().classify({"BTC-USDT-SWAP": c, "ETH-USDT-SWAP": c, "SOL-USDT-SWAP": c}, resonance=SimpleNamespace(score_adjustment=5))
        self.assertIn(res.structure_regime, {"trend", "transition"})
        self.assertEqual(res.trend_direction, "long")
        self.assertGreaterEqual(res.trend_persistence_score, 60)

    def test_fail_closed_wait_on_bad_input(self):
        res = MarketStructureClassifier().classify({"BTC-USDT-SWAP": []})
        self.assertEqual(res.structure_regime, "wait")
        self.assertIn("no_valid_candles", res.reason_codes)

    def test_chop_or_wait_not_trend_for_alternating_market(self):
        c = candles_chop()
        res = MarketStructureClassifier().classify({"BTC-USDT-SWAP": c, "ETH-USDT-SWAP": c})
        self.assertNotEqual(res.structure_regime, "trend")


if __name__ == "__main__":
    unittest.main()
