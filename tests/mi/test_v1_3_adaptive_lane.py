import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "/root/jarvis-mi")

from jarvis_mi.config_mi import MiConfig
from scripts.mi.mi_live_cycle import lane_profit_gate


@dataclass
class DummySize:
    notional: float


@dataclass
class DummyRisk:
    risk_mode: str = "normal"


class DummySignal:
    inst_id = "BTC-USDT-SWAP"
    side = "long"
    entry_ref = 100.0
    stop = 95.0
    expected_r = 4.8
    tp1_r = 1.2
    tp1_fraction = 0.5
    strategy_lane = "trend_probe"
    score = 68.0


def _cfg():
    return MiConfig(
        api_key="x", secret_key="x", passphrase="x", simulated="0",
        expected_uid="u", expected_main_uid="m", allowed_insts=("BTC-USDT-SWAP",),
        lane_min_expected_net_profit_pct={"trend_probe": 0.0145, "range_swing": 0.0138, "trend_confirmed": 0.015},
    )


def test_v13_near_miss_high_quality_candidate_passes_when_tp1_fee_positive(tmp_path):
    (tmp_path / "lane_feedback.jsonl").write_text("{}\n", encoding="utf-8")
    with patch("jarvis_mi.governors.STATE_DIR", tmp_path):
        ok, preview = lane_profit_gate(DummySignal(), DummyRisk(), DummySize(notional=6.0), equity=100.0, cfg=_cfg())
    assert ok is True
    assert preview["near_miss_pass"] is True
    assert preview["gate_version"] == "v1.4.1"


def test_v13_poor_candidate_still_rejected():
    sig = DummySignal()
    sig.score = 55.0
    sig.expected_r = 3.0
    ok, preview = lane_profit_gate(sig, DummyRisk(), DummySize(notional=5.0), equity=100.0, cfg=_cfg())
    assert ok is False
    assert preview["expected_trade_net_pct"] < preview["min_net_pct"]
