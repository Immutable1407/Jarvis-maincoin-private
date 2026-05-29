from __future__ import annotations
from datetime import datetime, timezone, timedelta
from .config_mi import REPORT_DIR, ensure_dirs, LEDGER_DIR, MiConfig
from .portfolio import portfolio_margin_used
import json


def _read_jsonl(name: str) -> list[dict]:
    path = LEDGER_DIR / name
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _count(path):
    return len(path.read_text(encoding="utf-8").splitlines()) if path.exists() else 0


def daily_brief() -> str:
    ensure_dirs()
    day = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    cfg = MiConfig.from_env()
    dec = LEDGER_DIR / "decisions.jsonl"
    fills = LEDGER_DIR / "fills.jsonl"
    trades = LEDGER_DIR / "trades.jsonl"
    decisions = _read_jsonl("decisions.jsonl")
    latest = decisions[-1] if decisions else {}
    positions = latest.get("positions") or []
    equity = latest.get("equity")
    margin_used = portfolio_margin_used(positions) if positions else 0.0
    margin_pct = (margin_used / float(equity)) if equity else 0.0
    blocked = [d for d in decisions[-100:] if d.get("reason") in {"portfolio_gate", "risk_engine_paused", "active_max_positions_reached"}]
    lane_state = "三车道百分比收益基线 + 两仓动态复利"
    text = [
        f"# Hermes Mi 主流币策略简报 {day}",
        "",
        f"- 状态：{cfg.system_version} {lane_state} 运行中。",
        f"- strategy_tag: {cfg.strategy_tag}",
        f"- 信号车道: trend_confirmed / trend_probe / range_swing",
        f"- 最低净收益门槛: {cfg.min_expected_net_profit_pct:.2%} equity",
        f"- 最大仓位: {cfg.active_max_positions}",
        f"- 第二仓: {'enabled' if cfg.enable_second_position else 'disabled'}",
        f"- 组合保证金硬上限: {cfg.portfolio_margin_cap_pct:.0%}",
        f"- 当前权益: {equity if equity is not None else 'unknown'} USDT",
        f"- 当前仓位: {len(positions)}/{cfg.active_max_positions}",
        f"- 估算组合保证金: {margin_used:.4f} USDT ({margin_pct:.1%})",
    ]
    for name, path in [("决策记录", dec), ("成交同步", fills), ("交易记录", trades)]:
        text.append(f"- {name}: {_count(path)} 条")
    text += [
        f"- 近100条被阻断/暂停决策: {len(blocked)} 条",
        "",
        "简要结论：v1.2.x 已切换为三车道百分比收益基线；重点观察 trend_probe/range_swing 是否真实贡献净收益、第二仓质量、组合保证金占用、guardian 动作和 market_state 是否长期 pause/chop。",
    ]
    out = "\n".join(text) + "\n"
    p = REPORT_DIR / "daily" / f"{day}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(out, encoding="utf-8")
    return out
