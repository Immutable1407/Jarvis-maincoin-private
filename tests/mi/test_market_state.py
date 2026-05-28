import unittest
from jarvis_mi.market_state import classify_market_state


def candles(start=100, step=1, n=80, vol=100):
    out=[]
    p=start
    for i in range(n):
        c=p+step
        out.append({'ts':i,'o':p,'h':max(p,c)+1,'l':min(p,c)-1,'c':c,'vol':vol})
        p=c
    return out

class TestMarketState(unittest.TestCase):
    def test_risk_on_allows_long(self):
        state = classify_market_state(candles(step=2), candles(step=1.5), candles(step=2.5), candles(step=0.8))
        self.assertEqual(state.btc_regime, 'risk_on')
        self.assertIn(state.direction_bias, {'long_only','both'})
        self.assertNotEqual(state.risk_budget, 'zero')

    def test_crash_pauses_new_entries(self):
        state = classify_market_state(candles(start=200, step=-5), candles(start=150, step=-4), candles(start=120, step=-5), candles(start=80, step=-3))
        self.assertEqual(state.btc_regime, 'crash')
        self.assertEqual(state.direction_bias, 'no_trade')
        self.assertEqual(state.risk_budget, 'zero')

if __name__ == '__main__':
    unittest.main()
