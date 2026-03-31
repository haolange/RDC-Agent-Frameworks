# Analyzer（分析与重建框架）

## 定位

> 当前状态：`incubating`
>
> 本目录仍处于方法论与骨架阶段，不纳入当前首发 GA / 商用品质门槛。

Analyzer 的目标不是修 bug，而是**把未知系统结构化为可解释模型**。

它的使命是：从一份或多份 capture 中，重建渲染管线与资源依赖，反推出 engine/material 的抽象模块，并生成可检索的知识库条目（供 Debug/Optimization 复用）。

## 成功标准（最小达标）

- pass graph 可视化可用（主要 pass、输入输出、依赖关系清晰）。
- shader/材质 block 指纹库可用（至少覆盖高频模块）。
- 可回答追溯查询（traceability）：
  - “某个像素/某个 pass 的颜色从哪里来？”

## 典型输入与输出

- 输入：一份或多份 capture、引擎/材质约定（若有）、资源命名规则、已知模块线索等。
- 输出：pass graph、资源依赖链、模块抽象（engine/material blocks）、指纹库条目、可检索知识索引与查询样例。

## 目录建议（说明性建议，不构成强约束）

参考 `debugger/` 的分层方式，可以按以下方向逐步演进：

- `common/`：平台无关的核心 Prompt 与知识契约（SSOT）
- `platforms/`：不同宿主/插件/工作台的适配层
- `docs/`：方法论、产物格式、术语与边界
- `knowledge/`：可检索知识库与会话产物沉淀
- `hooks/`：质量校验门禁（可选）

## 当前入口

当前最小 public entry 位于：

- `common/skills/rdc-analyst/SKILL.md`

它只承担 intake 与边界声明，不代表 `analyzer` 已完成平台化或 runtime contract 建设。
