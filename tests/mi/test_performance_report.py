import os
import unittest
from unittest import mock

from jarvis_mi.performance import daily_brief


class PerformanceReportTests(unittest.TestCase):
    def test_daily_brief_uses_current_v2_version_text(self):
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

        self.assertIn("v2.0.2-trend-wear-exit-loss-only", text)

        self.assertIn("trend_confirmed / trend_probe / range_swing", text)
        self.assertIn("v2当前regime/mode", text)
        self.assertIn("最低净收益门槛", text)
        self.assertIn("v1.4车道门槛", text)
        self.assertIn("Guardian退出计数", text)
        self.assertNotIn("v1.1.0 dynamic two-slot", text)


if __name__ == "__main__":
    unittest.main()


def test_realized_net_after_fees_for_day_filters_bjt_day():
    from jarvis_mi.performance import _realized_net_after_fees_for_day
    fills = [
        {'tradeId':'today', 'fillTime':'1779984000000', 'fillPnl':'1', 'fee':'-0.1'},
        {'tradeId':'other', 'fillTime':'1780070400000', 'fillPnl':'5', 'fee':'-0.5'},
    ]
    # 1779984000000 ms is 2026-05-29 08:00:00 BJT.
    net, n = _realized_net_after_fees_for_day(fills, '2026-05-29')
    assert n == 1
    assert round(net, 2) == 0.90
