# Codex 模板（平台模板）

<!-- BEGIN GENERATED COMMON-FIRST ADAPTER BLOCK -->
## Common-First Adapter Contract

- `common/` + package-local `tools/` 是共享执行内核，平台目录只是 adapter 壳层。
- 宿主可见的 native surface：`workspace_instructions`、`skills`、`mcp`、`per_role_config`、`multi_agent`。
- 目标合同来自 `common/config/platform_capabilities.json` 和 `common/config/framework_compliance.json`，不等同于当前 readiness。
- 当前 adapter 必须满足的 surface：`agents`、`skills`、`mcp`。
- 目标合同：`coordination_mode = staged_handoff`、`sub_agent_mode = puppet_sub_agents`、`peer_communication = via_main_agent`。
- 当前 adapter readiness 单独记录在 `common/config/adapter_readiness.json`：`adapter_in_progress`。
- `status_label` / `local_support` / `remote_support` / `enforcement_layer` 只描述仓库姿态，不代表 strict readiness。
- 严格执行必须由 shared harness、runtime lock、freeze state、artifact gate 和 finalization receipt 共同约束。
<!-- END GENERATED COMMON-FIRST ADAPTER BLOCK -->

当前目录是 Codex 的 workspace-native 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

入口规则：

- 当前宿主可直接访问本地进程、文件系统与 workspace，默认采用 local-first。
- 默认入口是 daemon-backed `CLI`；当前宿主的 `CLI` 与 `MCP` 都依赖同一 daemon-owned runtime / context。
- 只有用户明确要求按 `MCP` 接入时，才切换到 `MCP`。
- 遇到 `qrenderdoc` 风格的 shader IR 调试诉求时，不要只停在 `force_full_precision` 一类高层 patch。
  - 优先使用 `rd.shader.get_disassembly(session_id=<session_id>, target="SPIR-V ASM")` 拿 raw asm。
  - 再用 `rd.shader.edit_and_replace(session_id=<session_id>, source_text|diff_text, source_target="SPIR-V ASM", source_encoding="spirvasm")` 做精确替换。
  - 观察与验证链仍使用现有 `texture` / `export` / `macro` tool。
- 任务开始时，Agent 必须向用户说明当前采用的是 `CLI` 还是 `MCP`。
- 当前模板默认不预注册 MCP；若要启用，使用 `.codex/config.mcp.opt-in.toml` 的示例片段显式接入。
- 当前平台的 `local_support` / `remote_support` / `enforcement_layer` 以 `common/config/platform_capabilities.json` 中 `codex` 行为准。

使用方式：将 `debugger/common/` 与 `RDC-Agent-Tools` 覆盖到当前平台根目录下的 `common/` 和 `tools/`，运行 `python common/config/validate_binding.py --strict`，再使用当前平台根目录下的 `workspace/` 作为运行区。

约束：

- `common/` 只保留一个占位文件；正式共享正文仍由顶层 `debugger/common/` 提供。
- 未完成 `debugger/common/` 覆盖前，当前平台模板不可用。
- 未完成 `debugger/common/` 覆盖、`tools/` 覆盖或 binding 校验前，Agent 必须拒绝执行依赖平台真相的工作。
- 未提供可导入的 `.rdc` 时，Agent 必须以 `BLOCKED_MISSING_CAPTURE` 直接阻断。
- 当前平台的 remote 属于正式能力面，但统一服从 `single_runtime_owner`。
- OpenAI Codex Hooks 当前只提供有限 guardrail，因此当前 workspace-native 路径不引入 `.codex/hooks.json`。
- 当前平台的 enforcement 机制固定为 `runtime_owner + shared harness guard + audit artifacts`。
- Codex 的执行门禁固定为 `preflight -> intent_gate -> accept-intake -> dispatch-readiness / dispatch-specialist / specialist-feedback -> staged_handoff -> final-audit -> render-user-verdict`。
- 在 `artifacts/intake_gate.yaml` 通过前，不得进入 specialist dispatch 或 live `rd.*` 分析。

Sub-Agent 工作模型：

- `rdc-debugger` 是 public main skill。
- 当前平台的 `sub_agent_mode = puppet_sub_agents`。
- `rdc-debugger` 在 accepted intake 后必须先写出 `inputs/captures/manifest.yaml`、`capture_refs.yaml`、`notes/hypothesis_board.yaml`、`artifacts/intake_gate.yaml` 与 `artifacts/runtime_topology.yaml`。
- Sub-agents 之间不具备直接通信能力，所有依赖、冲突与下一轮 brief 都经 `rdc-debugger` 中转。
- 当前平台固定声明 `specialist_dispatch_requirement = required`、`host_delegation_policy = platform_managed`、`host_delegation_fallback = none`。
- 默认 `orchestration_mode = multi_agent`；只有用户显式要求不要 multi-agent context 时，才允许 `single_agent_by_user`。
- specialist dispatch 后，主 agent 必须先进入 `waiting_for_specialist_brief` 视图并持续汇总阶段回报。
- `curator_agent` 在 `multi_agent` 下仍是 finalization-required。
