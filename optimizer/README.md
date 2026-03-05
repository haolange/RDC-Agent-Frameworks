# Optimizer
## Multi-Agent Optimization Framework

Optimizer 的目标不是“给建议”，而是形成可复用、可验证的**优化闭环**：

- **可量化瓶颈归因**：给出 Top bottleneck，并解释其机制（不是“可能”）。
- **实验闭环**：至少完成一个反事实验证（开关/patch/配置 A/B），并给出收益预估与验证数据。

Optimization 的主驱动是“性能预算不变量”（frame time / bandwidth / overdraw / occupancy）：
- 把帧时间拆解到 **pass/event/资源** 维度，形成 frame breakdown。
- 针对预算违规项输出“归因→方案→验证”的链路，确保结论可追溯、可回归。

## 使命

- 从一份或多份 capture / profile / trace 中，重建可操作的性能模型与预算表。
- 输出可执行的优化方案清单（含收益预估、风险/回滚、验证方法）。
- 用实验数据证明“因果链成立”：优化动作是导致收益的关键变量。

## 成功标准（最小达标）

- 产出一份 frame breakdown（至少覆盖主要 pass / event 贡献）。
- bottleneck 归因明确且有机制解释（对应到具体 pass/event/资源）。
- 至少一个优化实验完成反事实验证，并记录验证数据。

## 典型输入 / 输出

- 输入：性能 profile、trace、指标面板、A/B 数据、资源依赖图、配置矩阵、成本账单等。
- 输出：瓶颈归因报告、可验证优化方案（含收益预估）、实验记录（A/B/开关）、回归验证结论、可检索知识条目。

## 目录建议（描述，不强制）

参考 `debugger/` 的分层方式，建议逐步演进到：

- `common/`：平台无关的核心 Prompt、契约与质量门槛（SSOT）
- `platforms/`：不同宿主/插件/工作台的适配层
- `docs/`：指标定义、实验方法、回归策略与报告模板
- `knowledge/`：历史优化案例、实验记录与索引
- `hooks/`：质量校验（例如：性能回归阈值、指标完整性检查）