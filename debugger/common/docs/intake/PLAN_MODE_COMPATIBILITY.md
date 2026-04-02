# Plan Mode Compatibility

本文定义宿主 Plan Mode 与 debugger framework 的结合方式。

## 基本口径

- 宿主 `Plan Mode` 是宿主协作模式，不是 debugger 自己定义的第二个 public skill。
- `rdc-debugger` 继续是唯一 public entrypoint。
- 当宿主处于 Plan Mode 时，`rdc-debugger` 应先运行内部 `Plan / Intake Phase`，把用户请求收敛为 `debug_plan`。
- 只有 `debug_plan.execution_readiness = ready` 后，才进入 `Audited Execution Phase`。

## 宿主与 framework 的职责边界

宿主 Plan Mode 负责：

- 提供多轮规划/澄清的交互容器
- 允许调用 skill 和 sub-agent

debugger framework 负责：

- `intent_gate`
- 规划型 sub-agent 的角色边界
- `debug_plan` contract
- execution 入口与严格链

## 规划型 Sub-Agent

Plan 阶段默认通过以下轻量 sub-agent 执行：

- `clarification_agent`
- `reference_contract_agent`
- `plan_compiler_agent`

orchestrator 只保留：

- 核心事实摘要
- 缺失输入列表
- `reference_contract` 结论
- 最终 `debug_plan`

orchestrator 不应保留：

- 冗长问答全文
- 全部中间推理
- 可由 sub-agent 局部持有的低价值上下文

## 严格执行链起点

严格执行链的真正起点是 `entry_gate`，而不是用户第一次唤起 `rdc-debugger`。

Plan 阶段不做：

- `entry_gate`
- `accept_intake`
- `intake_gate`
- case/run 初始化
- broker startup
- specialist dispatch

这些动作全部属于 `Audited Execution Phase`。
