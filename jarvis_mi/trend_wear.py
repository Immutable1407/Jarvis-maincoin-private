from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import time
from typing import Any

from .config_mi import LEDGER_DIR, STATE_DIR


def _floatish(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except Exception:
        return default


def _fill_position_side(row: dict, role: str) -> str | None:
    """Return the position side represented by a fill row when knowable.

    OKX hedge-mode fills have both order `side` (buy/sell) and `posSide`
    (long/short).  `posSide` is authoritative.  If it is missing, only infer
    from buy/sell when the lifecycle role is known; exit orders invert the
    order side, while entries follow it.  Some older synthetic rows used
    `side=long|short`, so preserve that as a direct position-side fallback.
    """
    pos_side = str(row.get("posSide") or row.get("pos_side") or "").lower()
    if pos_side in {"long", "short"}:
        return pos_side

    side = str(row.get("side") or "").lower()
    if side in {"long", "short"}:
        return side
    if role == "exit":
        if side == "sell":
            return "long"
        if side == "buy":
            return "short"
    if role == "entry":
        if side == "buy":
            return "long"
        if side == "sell":
            return "short"
    return None


def _trend_fill_loss(row: dict, side: str | None = None) -> bool:
    """True only for trend_confirmed closed-trade/exit loss fills.

    v2.0.1 counted entry rows with fillPnl=0 plus a negative fee as losses,
    which polluted TrendWearGovernor state.  v2.0.2 counts explicit exit fills
    (fill_role/order_role=exit), still supports legacy role-less rows with a
    non-zero realized PnL, and ignores fee-only rows.
    """
    lane = row.get("strategy_lane") or ""
    if lane != "trend_confirmed":
        return False

    fill_role = str(row.get("fill_role") or "").lower()
    order_role = str(row.get("order_role") or "").lower()
    role = "exit" if "exit" in {fill_role, order_role} else ("entry" if "entry" in {fill_role, order_role} else "")
    if role == "entry":
        return False

    if side:
        row_side = _fill_position_side(row, role)
        if row_side is not None and row_side != side:
            return False

    fill_pnl = _floatish(row.get("pnl") or row.get("realizedPnl") or row.get("fillPnl") or 0)
    fee = _floatish(row.get("fee") or 0)

    # Role-less legacy rows may include fees on entry fills.  Do not treat a
    # zero-realized-PnL fee as a closed-trade loss.
    if not role and abs(fill_pnl) < 1e-12:
        return False

    return (fill_pnl + fee) < 0


@dataclass(frozen=True)
class TrendWearState:
    wear_level: int
    actions: list[str]
    reason_codes: list[str]
    no_mfe_count: int = 0
    stopout_count: int = 0
    loss_count: int = 0
    cooldown_until: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class TrendWearGovernor:
    """Cold/local-ledger based trend wear detector.

    Any read failure leaves safe reduced defaults, never raises into hot path.
    """

    def __init__(self, ledger_dir: Path | None = None, state_dir: Path | None = None):
        self.ledger_dir = ledger_dir or LEDGER_DIR
        self.state_dir = state_dir or STATE_DIR

    def _read_jsonl(self, name: str, limit: int = 300) -> list[dict]:
        path = self.ledger_dir / name
        if not path.exists():
            return []
        rows: list[dict] = []
        for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        return rows

    def evaluate(self, inst_id: str | None = None, side: str | None = None, now_ts: float | None = None) -> TrendWearState:
        now_ts = now_ts or time.time()
        try:
            decisions = self._read_jsonl("decisions.jsonl")
            guardian = self._read_jsonl("guardian.jsonl")
            fills = self._read_jsonl("fills.jsonl")
            reasons: list[str] = []
            no_mfe = 0
            stopouts = 0
            losses = 0

            for row in decisions[-120:]:
                selected = row.get("selected") or {}
                if inst_id and selected.get("inst_id") not in (None, inst_id) and selected.get("instId") not in (None, inst_id):
                    continue
                if side and selected.get("side") not in (None, side):
                    continue
                lane = selected.get("strategy_lane") or row.get("strategy_lane")
                text = " ".join(str(x) for x in (selected.get("reason") or []) + [row.get("reason") or ""])
                if lane == "trend_confirmed" and ("no_mfe" in text or "false_breakout" in text):
                    no_mfe += 1

            for row in guardian[-120:]:
                actions = row.get("actions") or []
                for a in actions:
                    if inst_id and a.get("instId") not in (None, inst_id):
                        continue
                    raw = str(a.get("reason") or a.get("raw_reason") or a.get("cooldown_reason") or "").lower()
                    if "local_stop" in raw or "stop" in raw:
                        stopouts += 1
                    if "no_mfe" in raw:
                        no_mfe += 1

            for row in fills[-200:]:
                if inst_id and row.get("instId") not in (None, inst_id):
                    continue
                if _trend_fill_loss(row, side):
                    losses += 1

            cooldown_until = None
            cooldown_path = self.state_dir / "trend_wear_cooldown.json"
            if cooldown_path.exists():
                try:
                    data = json.loads(cooldown_path.read_text(encoding="utf-8"))
                    key = f"{inst_id or '*'}:{side or '*'}"
                    cooldown_until = float(data.get(key) or data.get("global") or 0) or None
                    if cooldown_until and cooldown_until > now_ts:
                        reasons.append("trend_wear_cooldown_active")
                except Exception:
                    reasons.append("trend_wear_cooldown_read_failed")

            if no_mfe >= 3 or stopouts >= 3 or losses >= 4 or (cooldown_until and cooldown_until > now_ts):
                level = 3
                actions = ["reduce_risk", "block_new_trend_entries", "demote_to_wait"]
            elif no_mfe >= 2 or stopouts >= 2 or losses >= 3:
                level = 2
                actions = ["demote_trend_to_transition", "reduce_risk"]
            elif no_mfe >= 1 or stopouts >= 1 or losses >= 1:
                level = 1
                actions = ["reduce_risk"]
            else:
                level = 0
                actions = []
            if no_mfe:
                reasons.append(f"no_mfe_count_{no_mfe}")
            if stopouts:
                reasons.append(f"stopout_count_{stopouts}")
            if losses:
                reasons.append(f"trend_loss_count_{losses}")
            if not reasons:
                reasons.append("trend_wear_clear")
            return TrendWearState(level, actions, reasons, no_mfe, stopouts, losses, cooldown_until)
        except Exception as exc:
            return TrendWearState(1, ["reduce_risk"], ["trend_wear_read_error", type(exc).__name__])
