import unittest
from dataclasses import dataclass

from jarvis_mi.config_mi import MiConfig
from jarvis_mi.market_state import MarketState
from jarvis_mi.portfolio import portfolio_allows_entry, portfolio_allows_sized_entry, portfolio_margin_used
from jarvis_mi.risk_engine import decide_risk


@dataclass
class Sig:
    inst_id: str = "SOL-USDT-SWAP"
    side: str = "long"
    score: float = 90.0
    expected_r: float = 2.5


class TestV11DynamicTwoSlot(unittest.TestCase):
    def test_config_defaults_enable_v1_1_two_slot_compounding(self):
        cfg = MiConfig(
            api_key="k",
            secret_key="s",
            passphrase="p",
            simulated="0",
            expected_uid="u",
            expected_main_uid="m",
            allowed_insts=("BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "BNB-USDT-SWAP"),
        )

        self.assertEqual(cfg.strategy_tag, "mi_v2_0_2_regime_adaptive_maincoin")

        self.assertGreater(cfg.min_expected_net_profit_pct, cfg.altcoin_profit_baseline_pct)
        self.assertIsNotNone(cfg.lane_min_expected_net_profit_pct)
        self.assertEqual(cfg.active_max_positions, 2)
        self.assertTrue(cfg.enable_second_position)
        self.assertAlmostEqual(cfg.portfolio_margin_cap_pct, 0.60)
        self.assertAlmostEqual(cfg.single_position_margin_cap_pct, 0.35)
        self.assertFalse(cfg.allow_mixed_direction_portfolio)

    def test_risk_engine_uses_higher_margin_but_moderate_leverage(self):
        state = MarketState("risk_on", "expansion", "long_only", "normal", "full", ["risk_on"])
        d = decide_risk(state, signal_score=92, volatility_pct=0.015, equity=100, recent_stopouts=0, resonance_risk_multiplier=1.0)
        self.assertIn(d.risk_mode, {"normal", "strong"})
        self.assertGreaterEqual(d.margin_pct, 0.22)
        self.assertLessEqual(d.margin_pct, 0.35)
        self.assertGreaterEqual(d.leverage, 8)
        self.assertLessEqual(d.leverage, 12)
        self.assertGreaterEqual(d.max_loss_pct, 0.02)
        self.assertLessEqual(d.max_loss_pct, 0.04)

    def test_high_volatility_reduces_v1_1_leverage_and_margin(self):
        state = MarketState("risk_on", "expansion", "long_only", "normal", "full", ["risk_on"])
        d = decide_risk(state, signal_score=92, volatility_pct=0.045, equity=100, recent_stopouts=0, resonance_risk_multiplier=1.0)
        self.assertLessEqual(d.leverage, 8)
        self.assertLess(d.margin_pct, 0.22)
        self.assertIn("high_vol_reduced", d.reason_codes)

    def test_second_position_allowed_but_third_rejected(self):
        one = [{"instId": "BTC-USDT-SWAP", "posSide": "long", "pos": "1"}]
        ok, reasons = portfolio_allows_entry(one, Sig(), active_max_positions=2, enable_second_position=True)
        self.assertTrue(ok, reasons)

        two = one + [{"instId": "ETH-USDT-SWAP", "posSide": "long", "pos": "1"}]
        ok, reasons = portfolio_allows_entry(two, Sig("BNB-USDT-SWAP", "long"), active_max_positions=2, enable_second_position=True)
        self.assertFalse(ok)
        self.assertIn("active_max_positions_reached", reasons)

    def test_same_symbol_and_mixed_direction_are_blocked(self):
        one = [{"instId": "BTC-USDT-SWAP", "posSide": "long", "pos": "1"}]
        ok, reasons = portfolio_allows_entry(one, Sig("BTC-USDT-SWAP", "long"), active_max_positions=2, enable_second_position=True)
        self.assertFalse(ok)
        self.assertIn("same_symbol_position_exists", reasons)

        ok, reasons = portfolio_allows_entry(one, Sig("ETH-USDT-SWAP", "short"), active_max_positions=2, enable_second_position=True, allow_mixed_direction_portfolio=False)
        self.assertFalse(ok)
        self.assertIn("mixed_direction_portfolio_blocked", reasons)

    def test_portfolio_margin_guard_blocks_over_sixty_percent(self):
        positions = [{"instId": "BTC-USDT-SWAP", "posSide": "long", "imr": "35"}]
        self.assertAlmostEqual(portfolio_margin_used(positions), 35.0)
        ok, reasons = portfolio_allows_sized_entry(
            positions=positions,
            signal=Sig("ETH-USDT-SWAP", "long"),
            new_margin=30.0,
            equity=100.0,
            active_max_positions=2,
            enable_second_position=True,
            portfolio_margin_cap_pct=0.60,
            single_position_margin_cap_pct=0.35,
            second_position_margin_cap_pct=0.30,
            allow_mixed_direction_portfolio=False,
        )
        self.assertFalse(ok)
        self.assertIn("portfolio_margin_cap_exceeded", reasons)


if __name__ == "__main__":
    unittest.main()
