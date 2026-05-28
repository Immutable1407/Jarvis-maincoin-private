import unittest
from jarvis_mi.market_state import MarketState
from jarvis_mi.risk_engine import decide_risk

class TestRiskEngine(unittest.TestCase):
    def test_chop_reduces_leverage(self):
        s = MarketState('chop','selective','both','slow','half',['x'])
        d = decide_risk(s, signal_score=80, volatility_pct=0.02, equity=100, recent_stopouts=0)
        self.assertLessEqual(d.leverage, 10)
        self.assertLess(d.margin_pct, 0.06)

    def test_crash_pauses(self):
        s = MarketState('crash','decay','no_trade','pause','zero',['x'])
        d = decide_risk(s, signal_score=90, volatility_pct=0.03, equity=100, recent_stopouts=0)
        self.assertEqual(d.risk_mode, 'paused')
        self.assertEqual(d.margin_pct, 0)

if __name__ == '__main__':
    unittest.main()
