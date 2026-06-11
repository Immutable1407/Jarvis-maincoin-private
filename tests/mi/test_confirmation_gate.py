import unittest
from types import SimpleNamespace

from jarvis_mi.confirmation import SecondConfirmationGate
from jarvis_mi.signal_score import Signal


def breakout_candles():
    out = []
    for i in range(20):
        c = 100 + i * 0.2
        out.append({"o": c, "h": c + 0.5, "l": c - 0.5, "c": c})
    # persistent close above previous range
    out += [{"o": 104, "h": 106, "l": 103.8, "c": 105.5}, {"o": 105.5, "h": 107, "l": 105, "c": 106.5}]
    return out


class TestSecondConfirmationGate(unittest.TestCase):
    def test_transition_blocks_normal_allows_probe_reason(self):
        sig = Signal("BTC-USDT-SWAP", "long", 80, [], 106, 102, 1.5, "trend_confirmed")
        structure = SimpleNamespace(structure_regime="transition", structure_confidence=60, trend_persistence_score=60, false_breakout_risk_score=40)
        d = SecondConfirmationGate().evaluate(sig, structure, breakout_candles())
        self.assertFalse(d.allow_normal)
        self.assertTrue(d.allow_probe)

    def test_trend_normal_requires_and_passes_confirmation(self):
        sig = Signal("BTC-USDT-SWAP", "long", 80, [], 106, 102, 1.5, "trend_confirmed")
        structure = SimpleNamespace(structure_regime="trend", structure_confidence=78, trend_persistence_score=78, false_breakout_risk_score=20)
        d = SecondConfirmationGate().evaluate(sig, structure, breakout_candles())
        self.assertTrue(d.allow_normal)
        self.assertGreaterEqual(d.confirmation_score, 60)

    def test_first_breakout_low_confidence_blocks(self):
        sig = Signal("BTC-USDT-SWAP", "long", 80, [], 100, 98, 1.5, "trend_confirmed")
        structure = SimpleNamespace(structure_regime="trend", structure_confidence=62, trend_persistence_score=61, false_breakout_risk_score=58)
        d = SecondConfirmationGate().evaluate(sig, structure, [{"h": 101, "l": 99, "c": 100}] * 10)
        self.assertFalse(d.allow_normal)


if __name__ == "__main__":
    unittest.main()
