import unittest
from typing import Any, cast
from jarvis_mi.execution import reduce_only_fraction, execute_entry
from jarvis_mi.okx_mi_client import OKXMiClient
from types import SimpleNamespace

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

    def test_reduce_only_close_formats_lot_size(self):
        from jarvis_mi.execution import reduce_only_close
        c=DummyClient(); p={'instId':'ETH-USDT-SWAP','pos':'1.234','posSide':'short'}
        rec = reduce_only_close(c, Cfg, p, 'full_close', lot_sz='0.01', min_sz='0.01')
        self.assertEqual(rec['event'], 'REDUCE_ONLY_PARTIAL')
        self.assertEqual(c.orders[0][2], '1.23')
        self.assertEqual(c.orders[0][3], 'short')

    def test_place_stop_algo_uses_okx_stop_loss_fields(self):
        class CaptureClient(OKXMiClient):
            def __init__(self):
                cfg = SimpleNamespace(td_mode='cross', api_key='k', secret_key='s', passphrase='p', simulated='0')
                super().__init__(cast(Any, cfg))
                self.body = None
            def _pos_mode(self):
                return 'long_short_mode'
            def request(self, method, path, params=None, body=None, auth=True):
                self.body = body
                return {'code': '0', 'data': [{'algoId': 's'}]}
        c = CaptureClient()
        c.place_stop_algo('ETH-USDT-SWAP', 'sell', '0.12', '98.5', pos_side='long')
        assert c.body is not None
        self.assertEqual(c.body['slTriggerPx'], '98.5')
        self.assertEqual(c.body['slOrdPx'], '-1')
        self.assertEqual(c.body['slTriggerPxType'], 'last')
        self.assertNotIn('triggerPx', c.body)
        self.assertNotIn('orderPx', c.body)
        self.assertEqual(c.body['posSide'], 'long')

if __name__ == '__main__':
    unittest.main()


class EntryFailClient(DummyClient):
    def __init__(self):
        super().__init__(); self.stops=[]; self.stop_fail=False
    def market_order(self, inst_id, side, sz, pos_side=None, reduce_only=False, cl_ord_id=None):
        self.orders.append((inst_id, side, sz, pos_side, reduce_only))
        return {'code':'0', 'data':[{}]}
    def set_leverage(self, *args, **kwargs):
        return {'code':'0'}
    def place_stop_algo(self, *args, **kwargs):
        self.stops.append(args); return {'code':'0', 'data':[{'algoId':'s'}]}

class EntryCfg(Cfg):
    default_leverage=5; margin_pct=0.1; max_loss_pct=0.02; max_margin_pct=0.35
    single_position_margin_cap_pct=0.35; active_max_positions=2; max_positions=2
    enable_second_position=True; portfolio_margin_cap_pct=0.6; second_position_margin_cap_pct=0.3
    allow_mixed_direction_portfolio=False

def test_execute_entry_rejects_order_missing_ordid_before_stop():
    c=EntryFailClient()
    sig=SimpleNamespace(inst_id='ETH-USDT-SWAP', side='long', entry_ref=100.0, stop=98.0, score=80, reason=[])
    inst={'ctVal':'1','lotSz':'0.01','minSz':'0.01','tickSz':'0.01'}
    try:
        execute_entry(c, EntryCfg, inst, sig, equity=100.0, positions=[])
    except RuntimeError as e:
        assert 'entry_order_missing_ordid' in str(e)
    else:
        raise AssertionError('expected RuntimeError')
    assert c.stops == []


class EntryStopFailClient(EntryFailClient):
    def market_order(self, inst_id, side, sz, pos_side=None, reduce_only=False, cl_ord_id=None):
        self.orders.append((inst_id, side, sz, pos_side, reduce_only))
        return {'code':'0', 'data':[{'ordId':'ENTRY1'}]}
    def place_stop_algo(self, *args, **kwargs):
        self.stops.append(args); return {'code':'1', 'msg':'bad stop'}

def test_execute_entry_records_critical_when_stop_fails_after_order(tmp_path, monkeypatch):
    import jarvis_mi.ledger as ledger
    monkeypatch.setattr(ledger, 'LEDGER_DIR', tmp_path)
    import jarvis_mi.execution as execution
    monkeypatch.setattr(execution, 'append_jsonl', ledger.append_jsonl)
    c=EntryStopFailClient()
    sig=SimpleNamespace(inst_id='ETH-USDT-SWAP', side='long', entry_ref=100.0, stop=98.0, score=80, reason=[])
    inst={'ctVal':'1','lotSz':'0.01','minSz':'0.01','tickSz':'0.01'}
    try:
        execute_entry(c, EntryCfg, inst, sig, equity=100.0, positions=[])
    except RuntimeError as e:
        assert 'entry_stop_algo_failed_after_order:ENTRY1' in str(e)
    else:
        raise AssertionError('expected RuntimeError')
    text=(tmp_path/'trades.jsonl').read_text()
    assert 'ENTRY_ORDER_ACCEPTED_PENDING_STOP' in text
    assert 'CRITICAL_ENTRY_STOP_FAILED_AFTER_ORDER' in text
    assert 'ENTRY1' in text
