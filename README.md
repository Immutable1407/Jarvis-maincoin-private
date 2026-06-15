> **Archive notice (2026-06-15):** Hermes Mi is now a closed historical experiment. Active development/trading moved to Matrix Account / Unified Jarvis v1.0.0. See `docs/EXPERIMENT_CLOSEOUT_20260615.md`.

# Jarvis 主流币策略（Hermes Mi）

这是 Sir 的 OKX 主流币永续合约策略私人归档仓库，对应 VPS 实盘目录 `/root/jarvis-mi`。仓库只保存代码、测试、中文说明和非敏感文档；不保存 API key、Webhook、账户余额、持仓、成交流水、日报或运行时状态。

## 当前董事会存档版本

- 实验状态（2026-06-14）：**进入收尾归档期**。Hermes Mi 已完成主流币独立策略从三车道百分比利润、lane 归因，到 v2.0.x regime-adaptive foundation 的实验使命；后续不再作为主要优化方向。实盘 cron 可继续小资金运行 1–2 天作为 Unified Jarvis 的对照组，但新增策略研发重心转向 `/root/jarvis-unified`。
- 收尾结论：Mi 证明主流币策略不能只做“少币种山寨系统”，必须有结构分类、趋势磨损、二次确认、range survive、相关性和退出归因；这些模块将作为 Unified 的 maincoin sleeve 参考。
- 归档用途：保留 BTC/ETH/SOL/BNB 主流币结构-first 交易框架、TrendWearGovernor、ModeRouter、RiskLadderV2、lane/exit attribution 等实现。

- 当前版本：`v2.0.2-trend-wear-exit-loss-only`
- 策略标签：`mi_v2_0_2_regime_adaptive_maincoin`
- 性质：v2.0.x regime-adaptive foundation 上的 bugfix；修复 TrendWearGovernor 将 entry fee 当 trend loss 的污染，不改变交易阈值、仓位、杠杆或风险预算。
- 标的范围：`BTC-USDT-SWAP`、`ETH-USDT-SWAP`、`SOL-USDT-SWAP`、`BNB-USDT-SWAP`
- 账户边界：专用 OKX 子账户 UID `845800098641991226`，只读取 `HERMES_MI_OKX_*` 凭证。
- 热路径：纯 Python 确定性执行；LLM 不进入下单/止损/守护链路。

## 策略逻辑摘要

Hermes Mi 是主流币趋势/共振策略，核心不是高频扫全市场，而是在 BTC、ETH、SOL、BNB 四个高流动性主流币之间寻找质量足够高的趋势机会。

- 市场结构：v2.0.x 使用 `MarketStructureClassifier` 识别 trend / transition / chop / wait。
- Trend wear：只根据 closed-trade / exit loss、no-MFE、stopout 等真实磨损降风险；entry fee-only fills 不得污染 `trend_loss_count_*`。
- 模式路由：`ModeRouter` 决定 TREND / TRANSITION / CHOP / WAIT；WAIT 禁止新开仓。
- 二次确认：TREND normal risk 需要 SecondConfirmationGate；TRANSITION 只允许 probe。
- Range survive：CHOP 默认 WAIT，只有质量、边界、费用条件达标才允许 range_swing。
- 入场车道：`trend_confirmed`、`trend_probe`、`range_swing`。
- 共振评分：比较 BTC/ETH/SOL/BNB 的同向、分化和强弱关系。
- 利润门槛：按权益百分比和 lane 动态设定，不用固定 USDT 小目标。
- 仓位约束：默认最多 2 个活动仓位；组合保证金硬上限 60%；禁止默认多空混合组合。
- Guardian：本地硬止损、保本、部分止盈、移动止损；止损状态单调，不允许越守越松。
- 归因层：成交、lane、near-miss、退出原因和日结报告关联，方便 GPT-5.5/Sir 做后续策略审查。

## 历史版本变迁

- `v1.0.0`：主流币独立策略初始归档。
- `v1.1.0`：两仓位/复利风控框架成型。
- `v1.2.0`：三车道百分比利润引擎；从固定收益目标改为权益百分比门槛。
- `v1.2.1`：日报版本与元数据一致性修补。
- `v1.3.0`：自适应 lane 利润引擎，按市场状态和信号质量调整机会门槛。
- `v1.4.0`：lane 归因、near-miss 反馈冷却、同向相关性 governor、Guardian 退出冷却。
- `v1.4.1`：entry/report fail-loud 热修复；OKX entry ordId/止损响应校验、BJT 日级 PnL。
- `v1.4.2`：归因增强；新增 attribution 模块、只读审计脚本、增强日结归因，不改变交易行为。
- `v1.4.3`：OKX stop-algo schema 热修复；入场后独立止损 algo 使用 `slTriggerPx/slOrdPx/slTriggerPxType`，避免 OKX 50015。
- `v2.0.0`：regime-adaptive foundation；引入市场结构分类、trend-wear、模式路由、二次确认、range-survive、RiskLadderV2。
- `v2.0.1`：entry-stop observability + reduce-only close quantization readiness。
- `v2.0.2`：TrendWearGovernor exit-loss-only bugfix；entry fee-only fills 不再触发 trend wear。

## 仓库结构

- `jarvis_mi/`：主流币策略核心代码。
- `scripts/mi/`：cron/运维脚本；`mi_live_cycle.py` 可能触发实盘下单。
- `tests/mi/`：回归测试。
- `docs/`：架构、运行手册、版本发布说明。
- `AGENTS.md`：给未来 AI agent 的项目边界、红线和命令速查。
- `VERSIONING.md`：版本标签含义。

## 验证命令

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 -m pytest -q tests/mi -o 'addopts='
python3 scripts/mi/mi_healthcheck.py
python3 scripts/mi/mi_sync_fills.py
python3 scripts/mi/mi_attribution_audit.py
```

`mi_live_cycle.py` 和 `mi_guardian.py` 属于实盘链路脚本，只有在明确需要实盘动作或运维检查时运行。

## 安全边界

私有 GitHub 不是秘密库。以下内容永不提交：`.env`、API key、OKX 凭证、Feishu webhook、账户/持仓/成交 JSON、运行时 ledger、日报、`data/`、`reports/`。
