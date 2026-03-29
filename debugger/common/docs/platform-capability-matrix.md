# Platform Capability Matrix（平台能力矩阵）

本矩阵是 `common/config/platform_capabilities.json` 的文档镜像，不是独立 SSOT。

| 平台 Platform | Coordination Mode | Sub-Agent Mode | Peer Communication | Agent Description | Dispatch Topology | Default Entry | Allowed Entry Modes | Local Live Policy | Remote Live Policy | Local Support | Remote Support | Enforcement |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Code Buddy | `concurrent_team` | `team_agents` | `direct` | `independent_files` | `mesh` | `CLI` | `CLI, MCP` | `multi_context_multi_owner` | `single_runtime_owner` | `verified` | `verified` | `hooks` |
| Claude Code | `concurrent_team` | `team_agents` | `direct` | `independent_files` | `mesh` | `CLI` | `CLI, MCP` | `multi_context_multi_owner` | `single_runtime_owner` | `verified` | `verified` | `hooks` |
| Copilot CLI | `staged_handoff` | `puppet_sub_agents` | `via_main_agent` | `independent_files` | `hub_and_spoke` | `CLI` | `CLI, MCP` | `multi_context_orchestrated` | `single_runtime_owner` | `verified` | `verified` | `hooks` |
| Copilot IDE | `staged_handoff` | `puppet_sub_agents` | `via_main_agent` | `independent_files` | `hub_and_spoke` | `CLI` | `CLI, MCP` | `multi_context_orchestrated` | `single_runtime_owner` | `verified` | `verified` | `runtime_owner` |
| Claude Desktop | `workflow_stage` | `instruction_only_sub_agents` | `none` | `spawn_instruction_only` | `workflow_serial` | `MCP` | `MCP only` | `single_runtime_owner` | `single_runtime_owner` | `degraded` | `serial_only` | `runtime_owner` |
| Manus | `workflow_stage` | `instruction_only_sub_agents` | `none` | `spawn_instruction_only` | `workflow_serial` | `MCP` | `MCP only` | `single_runtime_owner` | `single_runtime_owner` | `degraded` | `serial_only` | `runtime_owner` |
| Codex | `staged_handoff` | `puppet_sub_agents` | `via_main_agent` | `independent_files` | `hub_and_spoke` | `CLI` | `CLI, MCP` | `multi_context_orchestrated` | `single_runtime_owner` | `verified` | `verified` | `runtime_owner` |
| Codex Plugin | `staged_handoff` | `puppet_sub_agents` | `via_main_agent` | `skill_files` | `hub_and_spoke` | `CLI` | `CLI, MCP` | `multi_context_orchestrated` | `single_runtime_owner` | `verified` | `verified` | `runtime_owner` |
| Cursor | `staged_handoff` | `puppet_sub_agents` | `via_main_agent` | `independent_files` | `hub_and_spoke` | `CLI` | `CLI, MCP` | `multi_context_orchestrated` | `single_runtime_owner` | `verified` | `verified` | `hooks` |

## 说明

- `sub_agent_mode` 描述宿主的 agentic 形态，不等于 runtime 并行能力。
- `team_agents` 只表示子 agent 之间可直接通信；当前只有 `claude-code` 与 `code-buddy` 属于这一档。
- `puppet_sub_agents` 表示存在多个 specialist，但 specialist 之间不能直连；所有依赖、冲突与下一轮 brief 都经主 agent 中转。
- `instruction_only_sub_agents` 表示宿主支持 sub agent runtime，但不承载独立 agent 描述文件；如需子 agent，只能在主 agent 实例化时注入 instruction。
- `staged_handoff` 是 `workflow_stage` 与 `concurrent_team` 之间的中间形态；它是 `hub-and-spoke` 多轮接力，不是单 agent 串行切换。
- `staged_handoff local` 允许多 specialist 各自持有独立 context，但所有依赖与裁决必须经 `rdc-debugger`。
- `workflow_stage` 是串行 specialist 流，不是“无 sub agent”。
- `remote` 支持 multi-agent coordination，但所有平台都服从 `single_runtime_owner`。
- `local` 只有在 `coordination_mode=concurrent_team` 且 `sub_agent_mode=team_agents` 时，才允许 `multi_context_multi_owner`；`staged_handoff` 平台的 local 则收敛为 `multi_context_orchestrated`。
- `Enforcement` 中的 `hooks` / `runtime_owner` 只描述执行门禁落点；最终合规仍以 `artifacts/run_compliance.yaml` 为准。
