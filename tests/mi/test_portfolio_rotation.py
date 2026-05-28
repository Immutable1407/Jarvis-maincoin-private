import unittest
from jarvis_mi.portfolio import portfolio_allows_entry
from jarvis_mi.rotation import should_rotate

class Sig:
    inst_id='SOL-USDT-SWAP'; side='long'; score=90; expected_r=2.5

class TestPortfolioRotation(unittest.TestCase):
    def test_second_position_disabled(self):
        ok, reasons = portfolio_allows_entry([{'instId':'BTC-USDT-SWAP','posSide':'long','pos':'1'}], Sig(), active_max_positions=1)
        self.assertFalse(ok)
        self.assertIn('active_max_positions_reached', reasons)

    def test_rotation_threshold(self):
        decision = should_rotate(hold_score=50, candidate_score=85, friction_cost=5, correlation_penalty=5)
        self.assertTrue(decision.rotate)
        self.assertGreater(decision.edge, 20)

if __name__ == '__main__':
    unittest.main()
