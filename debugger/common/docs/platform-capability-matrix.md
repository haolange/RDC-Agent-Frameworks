# Platform Capability Matrix

本文按宿主平台能力定义各平台适配的“最佳实现上限”，并与 `common/config/platform_capabilities.json` 保持一致。

| Platform | Custom Agents/Subagents | Skills | Hooks | MCP | Per-Agent Model | Nested Delegation / Handoffs | Coordination Mode | Packaging |
|---|---|---|---|---|---|---|---|---|
| Code Buddy | Yes | Yes | Yes | Yes | Explicit | Yes | `concurrent_team` | Plugin bundle |
| Claude Code | Yes | Shared-entry | Yes | Yes | Alias-level | Prompt-directed | `concurrent_team` | Project config + subagents |
| Copilot CLI | Yes | Yes | Yes | Yes | Inherit-only | Limited | `staged_handoff` | CLI plugin |
| Copilot IDE | Yes | Yes (wrapper) | Documented boundary | Yes | Preferred | Yes | `staged_handoff` | `.github/agents` + MCP |
| Claude Desktop | No | No | No | Yes | Inherit | Workflow brief only | `workflow_stage` | Desktop MCP config |
| Manus | Workflow-level only | No | No | No | Workflow-level | Workflow-level | `workflow_stage` | Workflow package |
| Codex | Multi-agent config | Yes | No | Yes | Role config | Multi-agent | `concurrent_team` | Workspace-native |

## 解释

- `Code Buddy` 是当前最高完成度参考实现。
- `Claude Code` 必须具备 `subagents + hooks + MCP + model alias` 的真实落地文件，skill 通过共享入口引用 `common`。
- `Copilot CLI` 保持 plugin 形态，但 `CLI` 模式下禁止 discovery-by-trial-and-error；没有稳定 per-agent model 时只允许降级为 `inherit`。
- `Copilot IDE` 应使用 `.github/agents`、MCP、preferred model、handoffs 与 skill wrapper，不伪造宿主没有的一等 hooks。
- `Claude Desktop` 与 `Manus` 仅作为降级适配，不伪装成满配宿主。
- `Codex` 是 workspace-native 适配：`AGENTS.md`、`.agents/skills`、`.codex/config.toml`、`.codex/agents/*.toml` 共同构成宿主入口；`multi_agent` 当前按 experimental / CLI-first 理解。
- remote 不单独为某个平台发明新模式；所有平台统一服从 `single_runtime_owner`。

权威配置文件：

- `common/config/platform_capabilities.json`
