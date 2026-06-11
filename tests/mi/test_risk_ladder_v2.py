import unittest
from types import SimpleNamespace

from jarvis_mi.risk_ladder_v2 import RiskLadderV2


class TestRiskLadderV2(unittest.TestCase):
    def test_wait_zero(self):
        r = RiskLadderV2().decide(SimpleNamespace(mode="WAIT", mode_reason_codes=[]))
        self.assertEqual(r.leverage, 0)
        self.assertEqual(r.max_positions, 0)

    def test_chop_conservative_range_only(self):
        mode = SimpleNamespace(mode="CHOP", allow_range_swing=True, max_leverage=5, max_loss_pct=0.01, mode_reason_codes=[])
        r = RiskLadderV2().decide(mode, "range_swing")
        self.assertGreaterEqual(r.leverage, 3)
        self.assertLessEqual(r.leverage, 5)
        self.assertLessEqual(r.max_loss_pct, 0.01)
        blocked = RiskLadderV2().decide(mode, "trend_confirmed")
        self.assertEqual(blocked.risk_mode, "paused")

    def test_transition_probe_only(self):
        mode = SimpleNamespace(mode="TRANSITION", allow_trend_probe=True, max_leverage=6, max_loss_pct=0.015, mode_reason_codes=[])
        probe = RiskLadderV2().decide(mode, "trend_probe")
        normal = RiskLadderV2().decide(mode, "trend_confirmed")
        self.assertEqual(probe.risk_mode, "probe")
        self.assertEqual(normal.risk_mode, "paused")

    def test_trend_normal_requires_second_confirmation(self):
        mode = SimpleNamespace(mode="TREND", allow_trend_confirmed_normal=True, allow_trend_probe=True, max_leverage=10, max_loss_pct=0.03, mode_reason_codes=[])
        blocked = RiskLadderV2().decide(mode, "trend_confirmed", second_confirmation=False)
        allowed = RiskLadderV2().decide(mode, "trend_confirmed", second_confirmation=True)
        self.assertEqual(blocked.risk_mode, "paused")
        self.assertEqual(allowed.risk_mode, "normal")
        self.assertGreaterEqual(allowed.leverage, 8)

    def test_wear_only_reduces_risk(self):
        mode = SimpleNamespace(mode="TREND", allow_trend_confirmed_normal=True, allow_trend_probe=True, max_leverage=10, max_loss_pct=0.03, mode_reason_codes=[])
        clean = RiskLadderV2().decide(mode, "trend_confirmed", second_confirmation=True, wear_level=0)
        worn = RiskLadderV2().decide(mode, "trend_confirmed", second_confirmation=True, wear_level=2)
        self.assertLessEqual(worn.leverage, clean.leverage)
        self.assertLessEqual(worn.max_loss_pct, clean.max_loss_pct)


if __name__ == "__main__":
    unittest.main()
