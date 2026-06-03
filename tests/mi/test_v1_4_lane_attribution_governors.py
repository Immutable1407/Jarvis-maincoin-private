import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "/root/jarvis-mi")

from jarvis_mi.config_mi import MiConfig
from jarvis_mi.fills import enrich_fill_with_decision_attribution
from jarvis_mi.governors import (
    correlate_same_direction_governor,
    guardian_cooldown_allows_entry,
    lane_feedback_allows_near_miss,
    record_guardian_exit_cooldown,
)
from scripts.mi.mi_live_cycle import lane_profit_gate


@dataclass
class DummySize:
    notional: float


@dataclass
class DummyRisk:
    risk_mode: str = "normal"


class DummySignal:
    inst_id = "ETH-USDT-SWAP"
    side = "short"
    entry_ref = 100.0
    stop = 105.0
    expected_r = 4.6
    tp1_r = 1.2
    tp1_fraction = 0.5
    strategy_lane = "trend_probe"
    score = 68.0
    reason = ["unit"]


def _cfg(**kwargs):
    base = dict(
        api_key="x", secret_key="x", passphrase="x", simulated="0",
        expected_uid="u", expected_main_uid="m", allowed_insts=("BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"),
        lane_min_expected_net_profit_pct={"trend_probe": 0.0145, "range_swing": 0.0138, "trend_confirmed": 0.015},
    )
    base.update(kwargs)
    return MiConfig(**base)


def test_v14_version_and_strategy_tag_defaults():
    cfg = _cfg()
    assert cfg.system_version == "v1.4.1-entry-report-fail-loud-hotfix"
    assert cfg.strategy_tag == "mi_v1_4_1_entry_report_fail_loud_hotfix"


def test_v14_lane_profit_preview_carries_attribution_and_feedback_blocks_near_miss():
    sig = DummySignal()
    with tempfile.TemporaryDirectory() as td:
        state_dir = Path(td)
        # Recent lane loss disables loosening/near-miss; strict full threshold still applies.
        (state_dir / "lane_feedback.jsonl").write_text(
            '{"ts": "2026-06-02T00:00:00+00:00", "strategy_lane": "trend_probe", "realized_net_pct": -0.01}\n',
            encoding="utf-8",
        )
        with patch("jarvis_mi.governors.STATE_DIR", state_dir):
            ok, preview = lane_profit_gate(sig, DummyRisk(), DummySize(notional=6.0), equity=100.0, cfg=_cfg(), now_ts=1760000000)
    assert ok is False
    assert preview["gate_version"] == "v1.4.1"
    assert preview["strategy_lane"] == "trend_probe"
    assert preview["near_miss_pass"] is False
    assert preview["near_miss_feedback_allowed"] is False
    assert preview["expected_net_pct"] == preview["expected_trade_net_pct"]
    assert preview["expected_tp1_net_pct"] > 0


def test_v14_lane_feedback_fails_closed_when_state_unavailable():
    with tempfile.TemporaryDirectory() as td:
        missing_parent = Path(td) / "missing" / "state"
        with patch("jarvis_mi.governors.STATE_DIR", missing_parent):
            allowed, reason = lane_feedback_allows_near_miss("trend_probe", "ETH-USDT-SWAP", "short", now_ts=1760000000)
    assert allowed is False
    assert reason == "lane_feedback_unavailable"


def test_v14_correlated_same_direction_governor_blocks_low_quality_second_short():
    sig = DummySignal()
    sig.score = 80.0
    sig.strategy_lane = "trend_probe"
    positions = [{"instId": "BTC-USDT-SWAP", "posSide": "short", "margin": "20", "notionalUsd": "200"}]
    ok, detail = correlate_same_direction_governor(positions, sig, _cfg(), equity=100.0, new_size=DummySize(notional=150.0))
    assert ok is False
    assert detail["reason"] == "correlated_same_direction_low_quality_addition"
    assert detail["same_direction_count"] == 1
    assert detail["candidate_score"] == 80.0


def test_v14_correlated_same_direction_governor_allows_high_score_or_trend_confirmed():
    sig = DummySignal()
    sig.score = 84.0
    positions = [{"instId": "BTC-USDT-SWAP", "posSide": "short", "margin": "20"}]
    ok, detail = correlate_same_direction_governor(positions, sig, _cfg(), equity=100.0, new_size=DummySize(notional=100.0))
    assert ok is True
    assert detail["reason"] == "high_quality_same_direction_addition"
    sig.score = 70.0
    sig.strategy_lane = "trend_confirmed"
    ok, detail = correlate_same_direction_governor(positions, sig, _cfg(), equity=100.0, new_size=DummySize(notional=100.0))
    assert ok is True
    assert detail["reason"] == "high_quality_same_direction_addition"


def test_v14_guardian_exit_cooldown_by_reason_same_instrument_side_only():
    with tempfile.TemporaryDirectory() as td:
        with patch("jarvis_mi.governors.STATE_DIR", Path(td)):
            record_guardian_exit_cooldown("SOL-USDT-SWAP", "short", "guardian_local_stop_short mark=1 stop=2", now_ts=1000.0)
            ok, detail = guardian_cooldown_allows_entry("SOL-USDT-SWAP", "short", now_ts=1000.0 + 60 * 60)
            assert ok is False
            assert detail["cooldown_reason"] == "local_stop"
            ok, _ = guardian_cooldown_allows_entry("SOL-USDT-SWAP", "long", now_ts=1000.0 + 60 * 60)
            assert ok is True
            ok, _ = guardian_cooldown_allows_entry("SOL-USDT-SWAP", "short", now_ts=1000.0 + 4 * 60 * 60 + 1)
            assert ok is True


def test_v14_fill_enrichment_copies_decision_lane_fields():
    fill = {"instId": "ETH-USDT-SWAP", "side": "sell", "clOrdId": "MI123"}
    decision = {
        "selected": {"inst_id": "ETH-USDT-SWAP", "side": "short", "strategy_lane": "trend_probe"},
        "profit_preview": {"near_miss_pass": True, "expected_net_pct": 0.014, "expected_tp1_net_pct": 0.002},
    }
    enriched = enrich_fill_with_decision_attribution(fill, [decision])
    assert enriched["strategy_lane"] == "trend_probe"
    assert enriched["near_miss_pass"] is True
    assert enriched["expected_net_pct"] == 0.014
    assert enriched["expected_tp1_net_pct"] == 0.002
