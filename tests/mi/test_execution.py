import unittest
from jarvis_mi.execution import reduce_only_fraction

class DummyClient:
    def __init__(self):
        self.orders=[]
    def uid_tuple(self):
        return 'u','m','long_short_mode'
    def market_order(self, inst_id, side, sz, pos_side=None, reduce_only=False, cl_ord_id=None):
        self.orders.append((inst_id, side, sz, pos_side, reduce_only))
        return {'data':[{'ordId':'1'}]}

class Cfg:
    expected_uid='u'; expected_main_uid='m'; allowed_insts=('ETH-USDT-SWAP',); td_mode='cross'; strategy_tag='test'

class TestExecution(unittest.TestCase):
    def test_reduce_only_fraction_skips_below_min_size(self):
        c=DummyClient(); p={'instId':'ETH-USDT-SWAP','pos':'0.2','posSide':'long'}
        rec = reduce_only_fraction(c, Cfg, p, 0.3, 'tiny_tp', lot_sz='0.1', min_sz='0.1')
        self.assertEqual(rec['event'], 'REDUCE_ONLY_PARTIAL_SKIPPED')
        self.assertEqual(c.orders, [])

    def test_reduce_only_fraction_formats_lot_size(self):
        c=DummyClient(); p={'instId':'ETH-USDT-SWAP','pos':'1.234','posSide':'short'}
        rec = reduce_only_fraction(c, Cfg, p, 0.5, 'tp', lot_sz='0.01', min_sz='0.01')
        self.assertEqual(rec['event'], 'REDUCE_ONLY_PARTIAL')
        self.assertEqual(c.orders[0][2], '0.61')
        self.assertEqual(c.orders[0][3], 'short')

if __name__ == '__main__':
    unittest.main()
