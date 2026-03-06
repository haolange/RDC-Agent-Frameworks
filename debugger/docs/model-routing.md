# Model Routing

本文定义平台无关的角色到模型偏好矩阵，以及各平台的映射与降级方式。

## 全局角色偏好

- `team_lead`
  - 角色：orchestrator
  - 优先模型：`opus-4.6`
- `skeptic_agent`
  - 角色：verifier
  - 优先模型：`gpt-5.4`
- `curator_agent`
  - 角色：report / knowledge
  - 优先模型：`gemini-3.1-pro`
- `triage_agent`、`capture_repro_agent`、`pass_graph_pipeline_agent`、`pixel_forensics_agent`、`shader_ir_agent`、`driver_device_agent`
  - 角色：investigator
  - 优先模型：`grok-4.1` 或 `sonnet-4.6`

## 平台回退原则

- `code-buddy`
  - 使用显式模型字符串。
- `claude-code`
  - 使用 `opus` / `sonnet` alias；无法精确表达时按模型 family 回退，但不改角色边界。
- `copilot-cli`
  - 默认 `inherit`，保留角色分工与 agent 文案。
- `copilot-ide`
  - 使用 `preferred model` 表达；宿主忽略时也不改角色设计。
- `claude-work`、`manus`
  - 只保留角色语义或 workflow 语义，不承诺精确模型控制。

## 约束

- 不允许在平台 agent frontmatter 中手工散落写模型策略。
- 模型策略只能来自 SSOT，再由脚本生成或校验。

权威配置文件：

- `common/config/model_routing.json`
