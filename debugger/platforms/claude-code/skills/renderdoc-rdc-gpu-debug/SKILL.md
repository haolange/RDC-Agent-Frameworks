# RenderDoc/RDC GPU Debug Skill

## 任务目标

这个 skill 的目标是让 Agent 明确：当前任务是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题，而不是讨论一个抽象 framework。

## 必读顺序

1. `../../../../common/AGENT_CORE.md`
2. `../../../../docs/platform-capability-model.md`
3. `../../../../docs/platform-capability-matrix.md`
4. `../../../../docs/model-routing.md`
5. 若用户要求 `CLI` 模式：`./cli-mode-reference.md`

## 平台模式

### `MCP` 模式

- 允许 tool discovery。
- 允许先发现工具能力，再进行多步编排。

### `CLI` 模式

- 禁止 discovery-by-trial-and-error。
- 禁止靠 `--help`、命令枚举、随机试跑、观察式试错来摸索能力面。
- 用户明确要求 `CLI` 模式时，必须先阅读 `cli-mode-reference.md`，再执行任务。

## 工具边界

- 目标是驱动 `rd.*` / platform tools 处理 capture、session、event、resource、shader、driver 证据。
- 禁止自造工具名。
- 调用时优先检查共享响应契约中的 `ok` 与 `error_message`。

## 协作拓扑

- 当前平台默认 `coordination_mode = concurrent_team`。
- `concurrent_team` 只表示可以并行分工，不表示多个 Agent 可以共享同一个 live session。
- local 多 Agent 并行时，每条 live 调试链路都必须独占一个 `context/daemon`。
- 禁止多个 Agent 在同一 `context` 下并发维护多条 live 调试链路。
- remote 场景强制退化为 `single_runtime_owner`；其他专家只提交 brief / evidence request，不直接并发占用 live remote runtime。

## Baton / Rehydrate

- 需要跨轮次移交 live 调试上下文时，必须附带 `runtime_baton`。
- `capture_file_id`、`session_id`、`remote_id` 都只能作为短生命周期提示，不得成为唯一真相源。
- baton 恢复顺序以 `../../../../docs/runtime-coordination-model.md` 为准。

## 方向约束

- 出现 `hair_shading`、`precision`、`washout`、`blackout`、`Adreno_GPU` 这类组合时，禁止直接依据 screen-like 观测做根因裁决。
- 必须先建立 `causal_anchor`，再把 `RelaxedPrecision`、后处理阶段或 screen-space shader 线索提升为根因分析对象。

## 结案约束

- 结案前必须满足 `session_evidence.yaml`、`skeptic_signoff.yaml`、`action_chain.jsonl` 与 `.current_session` 的 artifact 合同。
- `skeptic_agent` 未完成 signoff 时，不得把结论当成最终结论。
