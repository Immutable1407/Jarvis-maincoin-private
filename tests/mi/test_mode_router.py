import unittest
from types import SimpleNamespace

from jarvis_mi.mode_router import ModeRouter


class TestModeRouter(unittest.TestCase):
    def test_chop_blocks_trend_normal_and_waits_without_quality_range(self):
        s = SimpleNamespace(structure_regime="chop", structure_confidence=60, range_quality_score=40, trend_persistence_score=20, false_breakout_risk_score=40, reason_codes=[])
        m = ModeRouter().route(s, wear=SimpleNamespace(wear_level=0, reason_codes=[]))
        self.assertEqual(m.mode, "CHOP")
        self.assertFalse(m.allow_trend_confirmed_normal)
        self.assertFalse(m.allow_range_swing)
        self.assertEqual(m.max_leverage, 0)

    def test_transition_probe_only(self):
        s = SimpleNamespace(structure_regime="transition", structure_confidence=55, range_quality_score=30, trend_persistence_score=50, false_breakout_risk_score=55, reason_codes=[])
        m = ModeRouter().route(s, wear=SimpleNamespace(wear_level=0, reason_codes=[]))
        self.assertEqual(m.mode, "TRANSITION")
        self.assertTrue(m.allow_trend_probe)
        self.assertFalse(m.allow_trend_confirmed_normal)
        self.assertFalse(m.allow_second_position)

    def test_trend_normal_demoted_by_wear(self):
        s = SimpleNamespace(structure_regime="trend", structure_confidence=80, range_quality_score=20, trend_persistence_score=80, false_breakout_risk_score=20, reason_codes=[])
        clean = ModeRouter().route(s, wear=SimpleNamespace(wear_level=0, reason_codes=[]))
        worn = ModeRouter().route(s, wear=SimpleNamespace(wear_level=2, reason_codes=["wear"]))
        self.assertTrue(clean.allow_trend_confirmed_normal)
        self.assertFalse(worn.allow_trend_confirmed_normal)
        self.assertLessEqual(worn.max_leverage, clean.max_leverage)

    def test_router_fail_closed(self):
        m = ModeRouter().route(object())
        self.assertIn(m.mode, {"WAIT", "CHOP", "TRANSITION", "TREND"})
        self.assertFalse(m.allow_trend_confirmed_normal)


if __name__ == "__main__":
    unittest.main()
