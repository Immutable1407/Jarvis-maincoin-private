from __future__ import annotations

import os
from dataclasses import dataclass
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
    default_leverage: int = 20
    margin_pct: float = 0.06
    min_margin_pct: float = 0.05
    max_margin_pct: float = 0.08
    max_loss_pct: float = 0.012
    min_expected_r: float = 1.5
    max_daily_realized_loss_pct: float = 0.06
    strategy_tag: str = "mi_v0_1_trend_bootstrap"

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
