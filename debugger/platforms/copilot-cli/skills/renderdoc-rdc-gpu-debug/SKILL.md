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

## 方向约束

- 出现 `hair_shading`、`precision`、`washout`、`blackout`、`Adreno_GPU` 这类组合时，禁止直接依据 screen-like 观测做根因裁决。
- 必须先建立 `causal_anchor`，再把 `RelaxedPrecision`、后处理阶段或 screen-space shader 线索提升为根因分析对象。

## 结案约束

- 结案前必须满足 `session_evidence.yaml`、`skeptic_signoff.yaml`、`action_chain.jsonl` 与 `.current_session` 的 artifact 合同。
- `skeptic_agent` 未完成 signoff 时，不得把结论当成最终结论。
