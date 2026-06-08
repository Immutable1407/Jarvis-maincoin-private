from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path("/root/jarvis-mi")
DATA_DIR = PROJECT_ROOT / "data" / "mi"
STATE_DIR = DATA_DIR / "state"
LEDGER_DIR = DATA_DIR / "ledgers"
REPORT_DIR = PROJECT_ROOT / "reports" / "mi"
ENV_PATH = Path("/root/.hermes/.env")


def load_env_file(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
            v = v[1:-1]
        os.environ.setdefault(k, v)


@dataclass(frozen=True)
class MiConfig:
    api_key: str
    secret_key: str
    passphrase: str
    simulated: str
    expected_uid: str
    expected_main_uid: str
    allowed_insts: tuple[str, ...]
    td_mode: str = "cross"
    max_positions: int = 1
    default_leverage: int = 10
    margin_pct: float = 0.25
    min_margin_pct: float = 0.05
    max_margin_pct: float = 0.35
    max_loss_pct: float = 0.03
    min_expected_r: float = 1.5
    max_daily_realized_loss_pct: float = 0.10
    system_version: str = "v1.4.2-attribution-enhancement"
    strategy_tag: str = "mi_v1_4_2_attribution_enhancement"
    # v1.2.0: percent-based profit baseline. Maincoin target slope should exceed
    # altcoin's dynamic per-trade equity share, not use a fixed USDT target.
    altcoin_profit_baseline_pct: float = 0.012
    maincoin_profit_baseline_multiplier: float = 1.35
    min_expected_net_profit_pct: float = 0.0162
    # v1.3.0: lane-aware adaptive gate. Full-trade net remains primary, but
    # high-quality near-miss candidates may pass when TP1 is fee-positive and
    # the portfolio is underused. This prevents the v1.2 static gate from
    # rejecting every viable trend_probe/range_swing sample by a few bps.
    lane_min_expected_net_profit_pct: dict = field(default_factory=lambda: {
        "trend_confirmed": 0.0150,
        "trend_probe": 0.0145,
        "range_swing": 0.0138,
    })
    near_miss_profit_gate_ratio: float = 0.92
    min_tp1_net_profit_pct: float = 0.0015
    near_miss_min_score: float = 66.0
    near_miss_min_resonance_adjustment: float = 0.0
    correlated_add_min_score: float = 84.0
    taker_fee_rate: float = 0.0005
    enable_three_lane_signals: bool = True
    # v1.1.0+ feature flags: two-slot maincoin compounding with portfolio hard caps.
    enable_breakeven: bool = True
    enable_partial_tp: bool = True
    enable_trailing: bool = True
    enable_rotation: bool = False
    enable_second_position: bool = True
    enable_dynamic_leverage: bool = True
    enable_market_state_exit: bool = True
    active_max_positions: int = 2
    portfolio_margin_cap_pct: float = 0.60
    single_position_margin_cap_pct: float = 0.35
    second_position_margin_cap_pct: float = 0.30
    allow_mixed_direction_portfolio: bool = False

    @classmethod
    def from_env(cls) -> "MiConfig":
        load_env_file()
        allowed = os.getenv(
            "HERMES_MI_ALLOWED_INSTS",
            "BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP,BNB-USDT-SWAP",
        )
        cfg = cls(
            api_key=os.getenv("HERMES_MI_OKX_API_KEY", ""),
            secret_key=os.getenv("HERMES_MI_OKX_SECRET_KEY", ""),
            passphrase=os.getenv("HERMES_MI_OKX_PASSPHRASE", ""),
            simulated=os.getenv("HERMES_MI_OKX_SIMULATED", "0"),
            expected_uid=os.getenv("HERMES_MI_OKX_EXPECTED_UID", ""),
            expected_main_uid=os.getenv("HERMES_MI_OKX_EXPECTED_MAIN_UID", ""),
            allowed_insts=tuple(x.strip() for x in allowed.split(",") if x.strip()),
        )
        missing = [
            name for name, val in [
                ("HERMES_MI_OKX_API_KEY", cfg.api_key),
                ("HERMES_MI_OKX_SECRET_KEY", cfg.secret_key),
                ("HERMES_MI_OKX_PASSPHRASE", cfg.passphrase),
                ("HERMES_MI_OKX_EXPECTED_UID", cfg.expected_uid),
                ("HERMES_MI_OKX_EXPECTED_MAIN_UID", cfg.expected_main_uid),
            ] if not val
        ]
        if missing:
            raise RuntimeError(f"Missing Hermes Mi env vars: {', '.join(missing)}")
        return cfg


def ensure_dirs() -> None:
    for p in [STATE_DIR, LEDGER_DIR, REPORT_DIR, REPORT_DIR / "daily", DATA_DIR / "fills", DATA_DIR / "candles"]:
        p.mkdir(parents=True, exist_ok=True)
