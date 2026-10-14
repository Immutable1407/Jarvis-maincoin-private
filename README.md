# Hermes Mi｜主流币永续合约策略实验

Hermes Mi 是针对 BTC、ETH、SOL、BNB 构建的 OKX 永续合约交易系统。项目通过市场结构分类、趋势磨损反馈、模式路由、二次确认和组合约束，探索主流币趋势交易与有限区间交易的执行框架，并保留成交和退出归因能力。

**独立实验已于 2026-06-15 收尾。** 根据 [收尾记录](docs/EXPERIMENT_CLOSEOUT_20260615.md)，资金已迁入 [Matrix Account / Unified Jarvis](https://github.com/Immutable1407/Jarvis-unified-private)，原执行、Guardian、健康检查、成交同步和日报任务已暂停。本仓库作为源码与研究归档保留。

## 归档基线

| 项目 | 值 |
| --- | --- |
| 代码版本 | `v2.0.2-trend-wear-exit-loss-only` |
| 策略标签 | `mi_v2_0_2_regime_adaptive_maincoin` |
| 标的 | `BTC-USDT-SWAP`、`ETH-USDT-SWAP`、`SOL-USDT-SWAP`、`BNB-USDT-SWAP` |
| 原运行目录 | `/root/jarvis-mi` |
| 凭证命名空间 | `HERMES_MI_OKX_*` |
| 交易决策 | 确定性 Python；LLM 不进入实时执行链路 |

文档中的历史实盘状态和账户信息仅描述相应记录日期。归档包含实现与发布记录，不包含最新生产探针结果。

## 策略如何工作

```text
账户隔离与标的白名单
  → 四币种 1H / 15m 行情、BTC 方向与币种共振
  → 市场结构分类与趋势磨损反馈
  → TREND / TRANSITION / CHOP / WAIT 模式
  → 信号车道、二次确认与区间质量检查
  → RiskLadderV2、预期费后收益与组合约束
  → 合约数量计算、入场与交易所止损
  → Guardian、成交对账、退出归因和日报
```

市场模式决定哪些候选可以继续接受评估，而不是直接生成订单：

| 模式 | 行为 |
| --- | --- |
| `TREND` | 正式趋势风险需要二次确认；趋势磨损和回撤可以降低风险 |
| `TRANSITION` | 只允许较小的试探仓位 |
| `CHOP` | 默认等待，仅允许通过边界、质量和成本条件的区间机会 |
| `WAIT` | 不开新仓 |

候选分为 `trend_confirmed`、`trend_probe` 和 `range_swing` 三条车道。预期费后收益按账户权益百分比和车道评估，部分接近门槛的候选还必须通过质量、TP1 成本与历史反馈条件。预期收益是计划时的估计值，并不等于实现收益。

## 主要模块

| 功能 | 实现 |
| --- | --- |
| 市场结构 | `market_structure.py`、`market_state.py` |
| 趋势磨损 | `trend_wear.py`：根据已平仓亏损、no-MFE 和止损等记录调低风险 |
| 模式与入场权限 | `mode_router.py`、`confirmation.py`、`range_engine.py` |
| 共振与信号 | `resonance.py`、`signal_score.py` |
| 风险与组合 | `risk_ladder_v2.py`、`portfolio.py`、`governors.py`、`sizing.py` |
| 执行与退出 | `execution.py`、`exits.py`、`scripts/mi/mi_guardian.py` |
| 证据与报告 | `fills.py`、`attribution.py`、`counterfactual.py`、`performance.py` |

v2.0.2 修复了趋势磨损统计中的关键口径：开仓成交常见的“已实现盈亏为零、手续费为负”不再被统计为趋势亏损；明确退出成交的费后亏损才参与相应计数。双向持仓成交优先使用 `posSide` 判断方向。详见 [v2.0.2 发布说明](docs/V2_0_2_RELEASE.md)。

## 组合与退出约束

默认最多两个活动仓位；组合、单仓和第二仓的保证金上限分别为权益的 60%、35% 和 30%。第二仓仍受市场模式与同向相关性约束；默认不混合多空组合，rotation 关闭。

入场后设置交易所独立止损。Guardian 在本地评估硬止损、保本、部分止盈和移动止损，按合约步长处理减仓数量，并记录退出状态。当前架构中保本与 trailing 主要由本地 Guardian 执行；交易所侧止损取消和替换的进一步加固仍是文档中的后续工作。

当入场已接受而止损创建失败时，执行层记录 `CRITICAL_ENTRY_STOP_FAILED_AFTER_ORDER`。这类记录用于暴露执行异常，不能解释为仓位已经获得保护。

## 仓库结构

```text
jarvis_mi/                 # 策略、风险、执行、归因与状态模块
scripts/mi/                # 交易周期、Guardian、同步、审计与日报入口
tests/mi/                  # 22 个测试文件，含 unittest 与 pytest 风格用例
docs/                      # 架构、运行手册、发布与收尾记录
AGENTS.md                  # 项目边界和历史部署约定
VERSIONING.md              # 版本约定
```

## 阅读与代码检查

建议先阅读 [架构说明](docs/HERMES_MI_ARCHITECTURE.md)，再查看 [v2.0.0 基础版本](docs/V2_0_0_RELEASE.md)、[v2.0.1 执行观测修补](docs/V2_0_1_RELEASE.md)、[v2.0.2 统计口径修补](docs/V2_0_2_RELEASE.md) 和 [最终收尾](docs/EXPERIMENT_CLOSEOUT_20260615.md)。

在仓库根目录进行语法检查：

```bash
export PYTHONPATH="$PWD"
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
```

已有测试入口：

```bash
python3 -m unittest discover -s tests/mi -v
python3 -m pytest -q tests/mi -o 'addopts='
```

第二条需要 `pytest`，用于补充第一条未发现的函数式用例。仓库未提供锁定依赖环境。`config_mi.py` 将运行数据固定在 `/root/jarvis-mi/data/mi`，本地恢复和测试时需先确认路径隔离。

## 历史运维入口

| 脚本 | 用途 |
| --- | --- |
| `mi_healthcheck.py` | 账户与状态检查，需运行环境和凭证 |
| `mi_sync_fills.py` | 读取交易所成交并更新本地账本 |
| `mi_attribution_audit.py` | 读取本地账本，汇总车道、near-miss、方向与退出归因 |
| `mi_daily_review.py` | 基于本地记录生成日报 |
| `mi_live_cycle.py` | 完整交易周期，通过门控后可以下单 |
| `mi_guardian.py` | 持仓管理，可以减仓或平仓 |

已有本地账本时，可按北京时间日期查看归因：

```bash
python3 scripts/mi/mi_attribution_audit.py --day 2026-06-14 --json
```

仅克隆仓库时没有历史账本，审计可能显示 `No fill data found.`。Mi 不使用 Unified 的实盘环境变量门控；不能把执行脚本当作离线检查命令。历史部署、暂停和恢复流程见 [Runbook](docs/RUNBOOK.md)。

## 研究结果与归档边界

项目保留了主流币结构分类、模式风险、成本约束、趋势磨损与退出归因的实现。交易所成交是已实现盈亏的依据，候选评分、预期收益和局部交易样本不能替代完整绩效评估。

本仓库未提交完整成交、账户快照、运行状态或训练式绩效汇总，无法仅由源码复核全周期收益。`data/`、运行时 `reports/`、凭证和 Webhook 均留在生产或本地归档中。账户隔离与凭证前缀不能与其他 Jarvis 项目混用。
