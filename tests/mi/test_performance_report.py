import os
import unittest
from unittest import mock

from jarvis_mi.performance import daily_brief


class PerformanceReportTests(unittest.TestCase):
    def test_daily_brief_uses_current_v1_2_version_text(self):
        env = {
            "HERMES_MI_OKX_API_KEY": "x",
            "HERMES_MI_OKX_SECRET_KEY": "x",
            "HERMES_MI_OKX_PASSPHRASE": "x",
            "HERMES_MI_OKX_EXPECTED_UID": "845800098641991226",
            "HERMES_MI_OKX_EXPECTED_MAIN_UID": "621655308511150593",
            "HERMES_MI_OKX_SIMULATED": "0",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            text = daily_brief()
        self.assertIn("v1.2.1-report-consistency", text)
        self.assertIn("trend_confirmed / trend_probe / range_swing", text)
        self.assertIn("最低净收益门槛", text)
        self.assertNotIn("v1.1.0 dynamic two-slot", text)


if __name__ == "__main__":
    unittest.main()
