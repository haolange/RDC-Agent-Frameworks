# RDC-Agent Frameworks

本仓库提供构建在 RenderDoc/RDC 平台能力之上的上层 Agent framework。

## 仓库定位与层级关系

本仓库不是“直接暴露 RenderDoc 运行时能力”的平台仓库，而是构建在底层 `RDC-Agent Tools` 之上的上层 framework。

两者解决的问题不同，而且是明确的上下层关系，不是替代关系：

- 本仓库负责“任务编排与认知组织”
  - 把用户目标翻译成阶段性任务与角色分工。
  - 决定什么时候做 discovery、什么时候建立 session、什么时候进入 event / resource / shader / driver 分析。
  - 提供业务护栏、术语约定、输出格式、artifact 合同，以及失败后的重试、重建、降级原则。
  - 让 Agent 在复杂多轮任务里保持像一个懂 RenderDoc 工作流的人，而不是只会零散调用工具。
- `RDC-Agent Tools` 负责“平台能力与运行时约束”
  - 暴露稳定的 `rd.*` tool 能力面，并以 catalog / contract 作为规范源。
  - 定义 `.rdc -> capture_file_id -> session_id -> frame/event focus` 的最小平台链路。
  - 说明 `context`、daemon、local session state、runtime internal objects、artifact、context snapshot 之间的关系。
  - 固化共享错误契约与句柄生命周期边界，限制平台语义漂移。

可以把两层的关系理解为：

- 本仓库像“作战条令 + 专家协作规范 + 质量门槛”。
- 底层 `RDC-Agent Tools` 像“武器系统 + 通信协议 + 指挥接口 + 状态机 + 故障语义”。

因此，本仓库关心的是：

- 为了完成用户目标，该怎么组织行动。
- 哪些角色介入，先后顺序如何。
- 结论需要满足哪些证据门槛与 artifact 合同。

而底层 `RDC-Agent Tools` 关心的是：

- 系统客观上允许什么动作。
- 动作之间如何衔接，状态如何演化。
- `capture_file_id`、`session_id`、`remote_id`、`active_event_id` 等句柄是什么、何时有效、何时失效。
- 调用失败时，应依据什么共享契约来解释 `ok`、`error_message`、`error.details`。

这层分离的意义在于：

- 上层 framework 可以持续演进 prompt、roles、workflow，而不改写平台真相。
- 底层平台可以收紧 contract、修正生命周期语义、扩展 tool 能力，而不把业务 workflow 混进平台定义。
- 无论更换多少套宿主适配、skill 或 prompt，Agent 都应建立在同一套 RenderDoc/RDC 平台真相之上，而不是依赖记忆、试错或 convenience wrapper 去猜运行时。

仓库当前状态并不追求“所有方向都已完成”，而是区分成熟度：

- `debugger/`
  - 当前最完整的 framework。
  - 聚焦 GPU 渲染 Bug 调试，强调不变量、证据链、反事实验证和知识沉淀。
- `analyzer/`
  - 仍处于骨架阶段。
  - 目标是把未知渲染系统重建为可解释模型，但尚未形成完整 framework 契约。
- `optimizer/`
  - 仍处于骨架阶段。
  - 目标是形成可验证的优化闭环，但尚未形成完整 framework 契约。

## 设计原则

- 上层 framework 只依赖平台第一性能力，不把某个历史实现名当成框架概念本身。
- 平台工具接入和路径发现属于 adapter/config 层，不属于 framework 真相。
- 平台无关的 Prompt、知识库、质量门槛应保持单一真相来源。
- 平台适配物可以因宿主不同而变化，但角色职责和工作流约束不应漂移。
- 在 `debugger/` 主链中，任何最终根因裁决都必须先建立 `causal_anchor`，禁止把“问题首次明显可见的阶段”直接当成“问题首次被引入的阶段”。

## 当前建议阅读顺序

1. `debugger/README.md`
2. `debugger/common/AGENT_CORE.md`
3. `debugger/docs/platform-capability-model.md`
4. `debugger/docs/cli-mode-reference.md`

