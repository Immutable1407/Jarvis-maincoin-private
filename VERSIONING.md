# Versioning

Hermes Mi 主流币策略使用语义化版本：`MAJOR.MINOR.PATCH`。

- MAJOR：策略边界或交易哲学变化。
- MINOR：同一架构下的重要能力增强。
- PATCH：bug 修复、报告一致性、归因增强等不改变核心交易哲学的小版本。

## 当前版本

- `v1.4.2` — attribution enhancement（2026-06-08）：新增冷路径归因层、只读 attribution audit、日报归因板块；不改变交易阈值、仓位、杠杆或 Guardian 行为。

## 历史版本

- `v1.0.0` — 初始主流币独立策略归档。
- `v1.1.0` — 两仓位/复利风控框架。
- `v1.2.0` — 三 lane 百分比利润引擎。
- `v1.2.1` — 日报版本与元数据一致性修补。
- `v1.3.0` — 自适应 lane 利润引擎。
- `v1.4.0` — lane 归因、near-miss 反馈冷却、相关性 governor。
- `v1.4.1` — entry/report fail-loud hotfix：OKX entry ordId/stop 响应校验和 BJT 日级 PnL。
