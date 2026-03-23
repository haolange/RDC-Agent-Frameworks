# Platform Capability Matrix（平台能力矩阵）

本矩阵是 `common/config/platform_capabilities.json` 的文档镜像，不是独立 SSOT。

| Platform | Custom Agents | Skills | Hooks | MCP | Per-Agent Model | Handoffs | Coordination Mode | Packaging |
|---|---|---|---|---|---|---|---|---|
| Code Buddy | Yes | Yes | Yes | Yes | Explicit | Prompt-directed | `concurrent_team` | Plugin bundle |
| Claude Code | Yes | Shared-entry | Yes | Yes | Alias-level | Prompt-directed | `concurrent_team` | Project config plus subagents |
| Copilot CLI | Yes | Yes | Yes | Yes | Explicit | Limited | `staged_handoff` | CLI plugin |
| Copilot IDE | Yes | Yes (wrapper) | Documented boundary | Yes | Preferred | Native | `staged_handoff` | `.github/agents` plus MCP |
| Claude Desktop | No | No | No | Yes | Inherit-only | Workflow brief only | `workflow_stage` | Desktop MCP config |
| Manus | Workflow-only | No | No | No | Inherit-only | Workflow-level | `workflow_stage` | Workflow package |
| Codex | Yes | Yes | No | Yes | Config-file | Multi-agent | `staged_handoff` | Workspace-native |
| Cursor | Yes | Yes | Yes | Yes | Explicit | Prompt-directed | `concurrent_team` | Project config plus rules |

## 说明

- `code-buddy`、`copilot-ide` 和 `copilot-cli` 在本仓中按显式 per-agent routing 宿主处理。
- `cursor` 与 `code-buddy`、`copilot-cli` 一样按显式 per-agent routing 宿主处理。
- `claude-code` 支持 per-agent routing，但可选模型族受宿主模型池限制，正式用户入口应固定为 session-wide `team-lead` agent；skills 仍按 shared-entry 装配，不把平台层写成第二套 skill SSOT。
- `claude-desktop` 和 `manus` 属于 inherit-only 的降级宿主。
- `codex` 保留 per-agent 配置文件，但当前批准的路由模型族统一为 GPT。
- remote / live bridge 只保留为 `experimental` 协作合同，不计入本矩阵的当前正式支持能力。
- remote live-debug 的 owner 仍遵守共享 runtime 规则：每条 live 链路只能有一个 runtime owner。
