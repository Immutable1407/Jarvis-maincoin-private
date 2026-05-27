import unittest
from jarvis_mi.sizing import compute_size

class TestSizing(unittest.TestCase):
    def test_contract_formula_btc(self):
        s = compute_size(equity=50, price=100000, stop=99000, ct_val='0.01', lot_sz='0.01', min_sz='0.01', leverage=20, margin_pct=0.06, max_loss_pct=0.012)
        self.assertGreater(float(s.sz), 0)
        self.assertLessEqual(s.stop_loss_usdt, 0.612)
    def test_min_size(self):
        s = compute_size(equity=50, price=600, stop=590, ct_val='0.01', lot_sz='1', min_sz='1', leverage=20, margin_pct=0.001, max_loss_pct=0.012)
        self.assertGreaterEqual(float(s.sz), 1)

if __name__ == '__main__':
    unittest.main()
