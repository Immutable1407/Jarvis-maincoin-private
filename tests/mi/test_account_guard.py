import unittest
from jarvis_mi.account_guard import assert_allowed_inst, AccountGuardError
from jarvis_mi.config_mi import MiConfig

class TestAccountGuard(unittest.TestCase):
    def cfg(self):
        return MiConfig(api_key='a', secret_key='b', passphrase='c', simulated='0', expected_uid='u', expected_main_uid='m', allowed_insts=('BTC-USDT-SWAP',))
    def test_allowed(self):
        assert_allowed_inst('BTC-USDT-SWAP', self.cfg())
    def test_blocked(self):
        with self.assertRaises(AccountGuardError):
            assert_allowed_inst('DOGE-USDT-SWAP', self.cfg())

if __name__ == '__main__':
    unittest.main()
