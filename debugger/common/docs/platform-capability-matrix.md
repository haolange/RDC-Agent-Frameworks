# 平台能力矩阵

本矩阵是 `common/config/platform_capabilities.json` 的文档镜像，不是独立 SSOT。

## 平台矩阵

| 平台 Platform | Coordination Mode | Sub-Agent Mode | Peer Communication | Agent Description | Dispatch Topology | Default Entry | Allowed Entry Modes | Local Live Policy | Remote Live Policy | Local Support | Remote Support | Enforcement Layer | Enforcement Tier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Code Buddy | `concurrent_team` | `team_agents` | `direct` | `independent_files` | `mesh` | `CLI` | `CLI, MCP` | `multi_context_multi_owner` | `single_runtime_owner` | `verified` | `verified` | `pseudo_hooks` | `pseudo-hooks` |
| Claude Code | `concurrent_team` | `team_agents` | `direct` | `independent_files` | `mesh` | `CLI` | `CLI, MCP` | `multi_context_multi_owner` | `single_runtime_owner` | `verified` | `verified` | `native_hooks` | `native-hooks` |
| Copilot CLI | `staged_handoff` | `puppet_sub_agents` | `via_main_agent` | `independent_files` | `hub_and_spoke` | `CLI` | `CLI, MCP` | `multi_context_orchestrated` | `single_runtime_owner` | `verified` | `verified` | `native_hooks` | `native-hooks` |
| Copilot IDE | `staged_handoff` | `puppet_sub_agents` | `via_main_agent` | `independent_files` | `hub_and_spoke` | `CLI` | `CLI, MCP` | `multi_context_orchestrated` | `single_runtime_owner` | `verified` | `verified` | `pseudo_hooks` | `pseudo-hooks` |
| Claude Desktop | `workflow_stage` | `instruction_only_sub_agents` | `none` | `spawn_instruction_only` | `workflow_serial` | `MCP` | `MCP only` | `single_runtime_owner` | `single_runtime_owner` | `degraded` | `serial_only` | `no_hooks` | `no-hooks` |
| Manus | `workflow_stage` | `instruction_only_sub_agents` | `none` | `spawn_instruction_only` | `workflow_serial` | `MCP` | `MCP only` | `single_runtime_owner` | `single_runtime_owner` | `degraded` | `serial_only` | `no_hooks` | `no-hooks` |
| Codex | `staged_handoff` | `puppet_sub_agents` | `via_main_agent` | `independent_files` | `hub_and_spoke` | `CLI` | `CLI, MCP` | `multi_context_orchestrated` | `single_runtime_owner` | `verified` | `verified` | `runtime_owner` | `pseudo-hooks` |
| Codex Plugin | `staged_handoff` | `puppet_sub_agents` | `via_main_agent` | `skill_files` | `hub_and_spoke` | `CLI` | `CLI, MCP` | `multi_context_orchestrated` | `single_runtime_owner` | `verified` | `verified` | `no_hooks` | `no-hooks` |
| Cursor | `staged_handoff` | `puppet_sub_agents` | `via_main_agent` | `independent_files` | `hub_and_spoke` | `CLI` | `CLI, MCP` | `multi_context_orchestrated` | `single_runtime_owner` | `verified` | `verified` | `pseudo_hooks` | `pseudo-hooks` |

## 说明

- `sub_agent_mode` 描述宿主 agentic 形态，不等于 runtime 并行 ceiling。
- `team_agents` 只表示 specialist 之间可直接通信；当前只有 `claude-code` 属于正式 `native-hooks + team_agents` 平台。
- `puppet_sub_agents` 表示存在稳定 specialist 角色，但 specialist 之间不能直连；所有依赖、冲突与下一轮 brief 都经主 agent 中转。
- `instruction_only_sub_agents` 表示宿主支持 sub agent runtime，但不承载独立 agent 描述文件；需要子 agent 时，只能由主 agent 在实例化时注入 instruction。
- `staged_handoff` 是 `hub-and-spoke` 多轮接力，不是单 agent 串行切换。
- `workflow_stage` 是串行 specialist 流，不是“无 sub agent”。
- `remote` 可以支持 multi-agent coordination，但所有平台都统一服从 `single_runtime_owner`。
- `Enforcement Layer` 只描述执行门禁落点；最终合规仍以 `artifacts/run_compliance.yaml` 为准。
- `Enforcement Tier` 是跨平台 harness 分级：
  - `native-hooks`：宿主能用原生 lifecycle hooks 触发 shared harness。
  - `pseudo-hooks`：宿主只能用 wrapper / rules / runtime guard 伪造严格 hooks。
  - `no-hooks`：宿主无法可靠 host-side 拦截，只能依赖 shared harness + final audit。
