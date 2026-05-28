import unittest
from jarvis_mi.exits import plan_exit_actions

class TestExits(unittest.TestCase):
    def test_breakeven_and_tp_one_shot(self):
        pos={'instId':'ETH-USDT-SWAP','pos':'1','posSide':'long','avgPx':'100','markPx':'113'}
        state={}
        actions = plan_exit_actions(pos, entry=100, initial_stop=90, mark=113, state=state, min_size=0.1)
        kinds = [a.kind for a in actions]
        self.assertIn('move_stop_breakeven', kinds)
        self.assertIn('partial_tp_1', kinds)

    def test_short_trailing(self):
        pos={'instId':'ETH-USDT-SWAP','pos':'1','posSide':'short','avgPx':'100','markPx':'80'}
        actions = plan_exit_actions(pos, entry=100, initial_stop=110, mark=80, state={'partial_tp_1': True, 'partial_tp_2': True}, min_size=0.1)
        self.assertTrue(any(a.kind == 'trailing_stop' for a in actions))

if __name__ == '__main__':
    unittest.main()
