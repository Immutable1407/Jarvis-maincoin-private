# Jarvis 主流币策略（Hermes Mi）

这是 Sir 的 OKX 主流币永续合约策略私人归档仓库，对应 VPS 实盘目录 `/root/jarvis-mi`。仓库只保存代码、测试、中文说明和非敏感文档；不保存 API key、Webhook、账户余额、持仓、成交流水、日报或运行时状态。

## 当前董事会存档版本

- 当前版本：`v1.4.3-stop-algo-schema-hotfix`
- 策略标签：`mi_v1_4_3_stop_algo_schema_hotfix`
- 性质：归因增强版本；不改变交易阈值、仓位、杠杆、风控或 Guardian 行为。
- 标的范围：`BTC-USDT-SWAP`、`ETH-USDT-SWAP`、`SOL-USDT-SWAP`、`BNB-USDT-SWAP`
- 账户边界：专用 OKX 子账户 UID `845800098641991226`，只读取 `HERMES_MI_OKX_*` 凭证。
- 热路径：纯 Python 确定性执行；LLM 不进入下单/止损/守护链路。

## 策略逻辑摘要

Hermes Mi 是主流币趋势/共振策略，核心不是高频扫全市场，而是在 BTC、ETH、SOL、BNB 四个高流动性主流币之间寻找质量足够高的趋势机会。

- 市场状态：用 1h 级别判断风险环境、趋势方向和波动状态。
- 入场车道：三条 lane：`trend_confirmed`、`trend_probe`、`range_swing`。
- 共振评分：比较 BTC/ETH/SOL/BNB 的同向、分化和强弱关系。
- 利润门槛：按权益百分比和 lane 动态设定，不用固定 USDT 小目标。
- 仓位约束：默认最多 2 个活动仓位；组合保证金硬上限 60%；禁止默认多空混合组合。
- Guardian：本地硬止损、保本、部分止盈、移动止损；止损状态单调，不允许越守越松。
- 归因层：v1.4.2 将成交、lane、near-miss、退出原因和日结报告关联，方便 GPT-5.5/Sir 做后续策略审查。

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
python3 scripts/mi/mi_attribution_audit.py
```

`mi_live_cycle.py` 和 `mi_guardian.py` 属于实盘链路脚本，只有在明确需要实盘动作或运维检查时运行。

## 安全边界

私有 GitHub 不是秘密库。以下内容永不提交：`.env`、API key、OKX 凭证、Feishu webhook、账户/持仓/成交 JSON、运行时 ledger、日报、`data/`、`reports/`。
