import unittest
from jarvis_mi.resonance import compute_resonance


def cs(last, prev):
    return [{'ts':0,'o':prev,'h':max(prev,last),'l':min(prev,last),'c':prev,'vol':1},{'ts':1,'o':prev,'h':max(prev,last),'l':min(prev,last),'c':last,'vol':1}]

class TestResonance(unittest.TestCase):
    def test_all_up_boosts_quality(self):
        r = compute_resonance({'BTC-USDT-SWAP': cs(110,100),'ETH-USDT-SWAP': cs(108,100),'SOL-USDT-SWAP': cs(115,100),'BNB-USDT-SWAP': cs(104,100)})
        self.assertEqual(r.mode, 'aligned_long')
        self.assertGreater(r.score_adjustment, 0)

    def test_btc_down_alt_up_is_divergent(self):
        r = compute_resonance({'BTC-USDT-SWAP': cs(95,100),'ETH-USDT-SWAP': cs(103,100),'SOL-USDT-SWAP': cs(106,100),'BNB-USDT-SWAP': cs(102,100)})
        self.assertIn('btc_alt_divergence', r.reason_codes)
        self.assertLessEqual(r.risk_multiplier, 0.75)

if __name__ == '__main__':
    unittest.main()
