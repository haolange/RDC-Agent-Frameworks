# Platform Capability Matrix（平台能力矩阵）

本矩阵是 `common/config/platform_capabilities.json` 的文档镜像，不是独立 SSOT。

| Platform | Custom Agents | Skills | Hooks | MCP | Default Entry | Allowed Entry Modes | Per-Agent Model | Handoffs | Coordination Mode | Packaging |
|---|---|---|---|---|---|---|---|---|---|---|
| Code Buddy | Yes | Yes | Yes | Yes | `CLI` | `CLI, MCP` | Explicit | Prompt-directed | `concurrent_team` | Plugin bundle |
| Claude Code | Yes | Yes | Yes | Yes | `CLI` | `CLI, MCP` | Alias-level | Prompt-directed | `concurrent_team` | Project config plus subagents |
| Copilot CLI | Yes | Yes | Yes | Yes | `CLI` | `CLI, MCP` | Explicit | Limited | `staged_handoff` | CLI plugin |
| Copilot IDE | Yes | Yes (wrapper) | Documented boundary | Yes | `CLI` | `CLI, MCP` | Preferred | Native | `staged_handoff` | `.github/agents` plus MCP |
| Claude Desktop | No | Yes (wrapper) | No | Yes | `MCP` | `MCP only` | Inherit-only | Workflow brief only | `workflow_stage` | Desktop MCP config |
| Manus | Workflow-only | Yes (wrapper) | No | Yes | `MCP` | `MCP only` | Inherit-only | Workflow-level | `workflow_stage` | Workflow package |
| Codex | Yes | Yes | No | Yes | `CLI` | `CLI, MCP` | Config-file | Multi-agent | `staged_handoff` | Workspace-native |
| Cursor | Yes | Yes | Yes | Yes | `CLI` | `CLI, MCP` | Explicit | Prompt-directed | `concurrent_team` | Project config plus rules |

## 说明

- `code-buddy`、`copilot-ide` 和 `copilot-cli` 在本仓中按显式 per-agent routing 宿主处理。
- `cursor` 与 `code-buddy`、`copilot-cli` 一样按显式 per-agent routing 宿主处理。
- `claude-code` 支持 per-agent routing，但可选模型族受宿主模型池限制；若宿主仍要求 session bootstrap agent，可保留 `rdc-debugger` 作为内部 bootstrap/orchestrator，而 public user entry 统一是 `rdc-debugger`。
- `codex`、`claude-code`、`code-buddy`、`copilot-cli`、`copilot-ide`、`cursor` 当前默认 `CLI`，但用户可强制切到 `MCP`。
- `claude-desktop` 和 `manus` 属于 inherit-only 的降级宿主，但工具入口只允许 `MCP`，仍提供 wrapper skill 作为统一入口语义。
- `codex` 保留 per-agent 配置文件，但当前批准的路由模型族统一为 GPT。
- remote / live bridge 只保留为 `experimental` 协作合同，不计入本矩阵的当前正式支持能力。
- remote live-debug 的 owner 仍遵守共享 runtime 规则：每条 live 链路只能有一个 runtime owner。
- remote live-debug 即便仍是 `experimental`，也应按 same-event truthful failure 解释：成功 trace 与结构化 blocked/runtime failure 都是当前可依赖的结果面，不能再把“没拿到 trace”误写成平台 silent fallback。
