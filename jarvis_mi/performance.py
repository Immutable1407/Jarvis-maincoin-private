from __future__ import annotations
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict
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


def _float(row: dict, *keys: str) -> float:
    for key in keys:
        try:
            val = row.get(key)
            if val not in (None, ""):
                return float(val)
        except Exception:
            continue
    return 0.0


def _dedupe_key(row: dict) -> str:
    for key in ("fill_sync_key", "tradeId", "billId"):
        if row.get(key):
            return f"{key}:{row.get(key)}"
    return "cmp:" + "|".join(str(row.get(k, "")) for k in ("ordId", "instId", "fillTime", "fillPx", "fillSz", "side"))


def _realized_net_after_fees(fills: list[dict]) -> tuple[float, int]:
    seen = set()
    total = 0.0
    for row in fills:
        key = _dedupe_key(row)
        if key in seen:
            continue
        seen.add(key)
        total += _float(row, "pnl", "realizedPnl", "fillPnl")
        total += _float(row, "fee")  # OKX fees are normally negative; rebates positive.
    return total, len(seen)




def _parse_fill_day_bjt(row: dict) -> str | None:
    raw = row.get("fillTime") or row.get("cTime") or row.get("ts") or row.get("timestamp") or row.get("time")
    if raw in (None, ""):
        return None
    try:
        if isinstance(raw, (int, float)) or str(raw).isdigit():
            val = float(raw)
            if val > 1e12:
                val /= 1000.0
            return datetime.fromtimestamp(val, timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
        txt = str(raw).replace("Z", "+00:00")
        return datetime.fromisoformat(txt).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    except Exception:
        return None


def _realized_net_after_fees_for_day(fills: list[dict], day: str) -> tuple[float, int]:
    return _realized_net_after_fees([row for row in fills if _parse_fill_day_bjt(row) == day])

def _lane_near_miss_summary(decisions: list[dict], fills: list[dict]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = defaultdict(lambda: {"decisions": 0, "near_miss": 0, "fills": 0})
    for d in decisions:
        selected = d.get("selected") or {}
        preview = d.get("profit_preview") or {}
        lane = selected.get("strategy_lane") or preview.get("strategy_lane") or preview.get("lane")
        if not lane:
            continue
        summary[lane]["decisions"] += 1
        if preview.get("near_miss_pass"):
            summary[lane]["near_miss"] += 1
    for f in fills:
        lane = f.get("strategy_lane")
        if lane:
            summary[lane]["fills"] += 1
    return dict(summary)


def _top_rejection(decisions: list[dict]) -> tuple[str, int]:
    c = Counter()
    for d in decisions[-100:]:
        reason = d.get("reason")
        if reason:
            c[str(reason)] += 1
        for r in d.get("rejected_candidates") or []:
            if r.get("reason"):
                c[str(r.get("reason"))] += 1
    return c.most_common(1)[0] if c else ("none", 0)


def _guardian_exit_counts(rows: list[dict]) -> Counter:
    c = Counter()
    for row in rows:
        actions = row.get("actions") if isinstance(row, dict) else []
        for action in actions or []:
            reason = str(action.get("reason") or action.get("raw_reason") or action.get("cooldown_reason") or "")
            if "local_stop" in reason:
                c["local_stop"] += 1
            elif "breakeven" in reason:
                c["breakeven"] += 1
            elif "trailing" in reason:
                c["trailing"] += 1
            elif "partial_tp_2" in reason or "tp2" in reason.lower() or "mfe" in reason.lower():
                c["tp2_mfe_no_penalty"] += 1
    return c


def daily_brief() -> str:
    ensure_dirs()
    day = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    cfg = MiConfig.from_env()
    dec = LEDGER_DIR / "decisions.jsonl"
    fills_path = LEDGER_DIR / "fills.jsonl"
    trades = LEDGER_DIR / "trades.jsonl"
    decisions = _read_jsonl("decisions.jsonl")
    fills = _read_jsonl("fills.jsonl")
    guardian = _read_jsonl("guardian.jsonl")
    latest = decisions[-1] if decisions else {}
    positions = latest.get("positions") or []
    equity = latest.get("equity")
    margin_used = portfolio_margin_used(positions) if positions else 0.0
    margin_pct = (margin_used / float(equity)) if equity else 0.0
    blocked = [d for d in decisions[-100:] if d.get("reason") in {"portfolio_gate", "risk_engine_paused", "active_max_positions_reached"}]
    lane_thresholds = getattr(cfg, "lane_min_expected_net_profit_pct", None) or {}
    lane_threshold_text = " / ".join(
        f"{lane}:{pct:.2%}" for lane, pct in lane_thresholds.items()
    ) or f"default:{cfg.min_expected_net_profit_pct:.2%}"
    realized_net, dedupe_fills = _realized_net_after_fees_for_day(fills, day)
    total_realized_net, total_dedupe_fills = _realized_net_after_fees(fills)
    lane_summary = _lane_near_miss_summary(decisions[-200:], fills[-200:])
    lane_summary_text = "; ".join(
        f"{lane}: decisions={v['decisions']}, near_miss={v['near_miss']}, fills={v['fills']}"
        for lane, v in sorted(lane_summary.items())
    ) or "none"
    top_reason, top_count = _top_rejection(decisions)
    guardian_counts = _guardian_exit_counts(guardian)
    guardian_text = ", ".join(f"{k}={v}" for k, v in sorted(guardian_counts.items())) or "none"
    position_text = "; ".join(
        f"{p.get('instId')} {p.get('posSide')} pos={p.get('pos')} upl={p.get('upl')}"
        for p in positions
    ) or "none"

    # ── v1.4.2 attribution summary ──
    from .attribution import summarize_attribution
    attr = summarize_attribution(fills, decisions, guardian, day=day)

    # 归因总览
    attr_overview = f"已实现费后净额: {attr['total_realized_net']:.4f} USDT, 手续费: {attr['total_fees']:.4f}, 去重成交: {attr['total_fill_count']}, 未知归因: {attr['unknown_attribution']['count']}"

    # Lane贡献
    lane_lines = []
    for lane_name, ld in attr["by_lane"].items():
        lane_lines.append(
            f"{lane_name}: net={ld['realized_net']:+.4f}  fills={ld['fill_count']}  "
            f"win/loss={ld['win_count']}/{ld['loss_count']}  "
            f"avg={ld['avg_net_per_fill']:+.4f}  fees={ld['fees']:.4f}"
        )
    lane_contrib = "; ".join(lane_lines) if lane_lines else "无"

    # Near-miss质量
    nm_normal = attr["by_near_miss"].get("false", {})
    nm_pass = attr["by_near_miss"].get("true", {})
    near_miss_text = (
        f"near-miss: net={nm_pass.get('realized_net', 0):+.4f} fills={nm_pass.get('fill_count', 0)}; "
        f"normal: net={nm_normal.get('realized_net', 0):+.4f} fills={nm_normal.get('fill_count', 0)}"
    )

    # 退出归因
    exit_lines = []
    for er, ed in attr["by_exit_rule"].items():
        if ed["fill_count"] > 0:
            exit_lines.append(f"{er}: net={ed['realized_net']:+.4f} fills={ed['fill_count']}")
    exit_text = "; ".join(exit_lines) if exit_lines else "无退出归因数据"

    # 需要观察
    observations = []
    if attr["unknown_attribution"]["count"] > max(3, attr["total_fill_count"] * 0.1):
        observations.append(f"未知归因过高({attr['unknown_attribution']['count']}/{attr['total_fill_count']})")
    for lane_name, ld in attr["by_lane"].items():
        if ld["fill_count"] >= 2 and ld["realized_net"] < 0:
            observations.append(f"{lane_name}有成交但净亏损({ld['realized_net']:+.4f})")
    watch_text = "; ".join(observations) if observations else "无特别关注项"

    lane_state = "v1.4.2车道归因 + 反馈near-miss + 同向相关仓位Governor + 冷路径归因报告"
    text = [
        f"# Hermes Mi 主流币策略简报 {day}",
        "",
        f"- 状态：{cfg.system_version} {lane_state} 运行中。",
        f"- strategy_tag: {cfg.strategy_tag}",
        f"- 信号车道: trend_confirmed / trend_probe / range_swing",
        f"- 最低净收益门槛: {cfg.min_expected_net_profit_pct:.2%} equity",
        f"- v1.4车道门槛: {lane_threshold_text}; near-miss≥{cfg.near_miss_profit_gate_ratio:.0%}、TP1费后为正且反馈未冷却",
        f"- 同向第二仓Governor: score≥{cfg.correlated_add_min_score:.0f}或trend_confirmed才允许低相关质量加仓",
        f"- 最大仓位: {cfg.active_max_positions}",
        f"- 第二仓: {'enabled' if cfg.enable_second_position else 'disabled'}",
        f"- 组合保证金硬上限: {cfg.portfolio_margin_cap_pct:.0%}",
        f"- 当前权益: {equity if equity is not None else 'unknown'} USDT",
        f"- 当前仓位: {len(positions)}/{cfg.active_max_positions}",
        f"- 当前仓位/UPL: {position_text}",
        f"- 估算组合保证金: {margin_used:.4f} USDT ({margin_pct:.1%})",
        # ── v1.4.2 attribution sections ──
        f"## 归因总览",
        f"- {attr_overview}",
        f"## Lane贡献",
        f"- {lane_contrib}",
        f"## Near-miss质量",
        f"- {near_miss_text}",
        f"## 退出归因",
        f"- {exit_text}",
        f"## 需要观察",
        f"- {watch_text}",
        # ── Legacy summary lines ──
        f"- 今日已实现费后净额(北京时间去重fills): {realized_net:.4f} USDT",
        f"- 今日去重成交数: {dedupe_fills}",
        f"- 全量累计费后净额(去重fills): {total_realized_net:.4f} USDT / {total_dedupe_fills} fills",
        f"- Lane/near-miss摘要: {lane_summary_text}",
        f"- 近100决策Top拒绝原因: {top_reason} x{top_count}",
        f"- Guardian退出计数: {guardian_text}",
    ]
    for name, path in [("决策记录", dec), ("成交同步", fills_path), ("交易记录", trades)]:
        text.append(f"- {name}: {_count(path)} 条")
    text += [
        f"- 近100条被阻断/暂停决策: {len(blocked)} 条",
        "",
        "简要结论：v1.4.2 归因增强版，保留v1.4.1全部交易行为，新增冷路径归因层可回答：各lane真实费后贡献、near-miss盈亏质量、Guardian退出规则效果、未知归因占比。v1.4.1/1.4.0 已加入车道归因、反馈式near-miss冷却、同向相关仓位Governor和Guardian原因冷却。",
    ]
    out = "\n".join(text) + "\n"
    p = REPORT_DIR / "daily" / f"{day}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(out, encoding="utf-8")
    return out
