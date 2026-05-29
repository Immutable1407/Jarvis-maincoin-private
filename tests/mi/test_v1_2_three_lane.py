import unittest

from jarvis_mi.signal_score import evaluate_inst
from jarvis_mi.risk_engine import decide_risk
from jarvis_mi.market_state import MarketState


def candles_from_prices(prices):
    out = []
    for i, p in enumerate(prices):
        prev = prices[i - 1] if i else p
        out.append({"ts": i, "o": prev, "h": max(prev, p) + 0.5, "l": min(prev, p) - 0.5, "c": p, "vol": 100})
    return out


class Cfg:
    enable_three_lane_signals = True


class TestV12ThreeLane(unittest.TestCase):
    def test_trend_probe_lane_exists_before_full_breakout(self):
        h1_prices = [100 + i * 0.2 for i in range(80)]
        m15_prices = [112 + i * 0.02 for i in range(80)]
        m15_prices[-2] = m15_prices[-3] - 0.8
        m15_prices[-1] = m15_prices[-3] + 0.2
        sig = evaluate_inst("SOL-USDT-SWAP", candles_from_prices(h1_prices), candles_from_prices(m15_prices), "bull", cfg=Cfg)
        self.assertEqual(sig.side, "long")
        self.assertIn(sig.strategy_lane, {"trend_probe", "trend_confirmed"})
        self.assertGreaterEqual(sig.score, 65)

    def test_lane_changes_risk_decision(self):
        state = MarketState("chop", "selective", "both", "slow", "half", ["btc_flat_or_mixed"])
        d = decide_risk(state, signal_score=68, volatility_pct=0.01, equity=100, strategy_lane="range_swing")
        self.assertEqual(d.risk_mode, "range")
        self.assertIn("lane_range_swing", d.reason_codes)


if __name__ == "__main__":
    unittest.main()
