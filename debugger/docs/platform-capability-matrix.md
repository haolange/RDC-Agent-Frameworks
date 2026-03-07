# Platform Capability Matrix

本文按宿主平台能力定义各平台适配的“最佳实现上限”，并与 `common/config/platform_capabilities.json` 保持一致。

| Platform | Custom Agents/Subagents | Skills | Hooks | MCP | Per-Agent Model | Nested Delegation / Handoffs | Coordination Mode | Packaging |
|---|---|---|---|---|---|---|---|---|
| Code Buddy | Yes | Yes | Yes | Yes | Explicit | Yes | `concurrent_team` | Plugin bundle |
| Claude Code | Yes | Yes | Yes | Yes | Alias-level | Yes | `concurrent_team` | Project config + subagents |
| Copilot CLI | Yes | Yes | Yes | Yes | Inherit-first | Limited | `staged_handoff` | CLI plugin |
| Copilot IDE | Yes | No first-class skill layer | Documented boundary | Yes | Preferred | Yes | `staged_handoff` | `.github/agents` + MCP |
| Claude Work | Yes | No first-class skill layer | No | Yes | Inherit | Weak | `staged_handoff` | Local plugin contract |
| Manus | Workflow-level only | No | No | No | Workflow-level | Workflow-level | `workflow_stage` | Workflow package |

## 解释

- `Code Buddy` 是当前最高完成度参考实现。
- `Claude Code` 必须具备 `subagents + hooks + MCP + model alias` 的真实落地文件。
- `Copilot CLI` 保持 plugin 形态，但 `CLI` 模式下禁止 discovery-by-trial-and-error。
- `Copilot CLI`、`Copilot IDE`、`Claude Work` 虽可表达一定程度的 agent / handoff，但 framework 默认按 `staged_handoff` 编排 live 调试。
- `Copilot IDE` 应使用 `.github/agents`、MCP、preferred model 与文档化边界，不伪造 CLI skill 目录。
- `Claude Work` 与 `Manus` 仅作为降级适配，不伪装成满配宿主。
- remote 不单独为某个平台发明新模式；所有平台统一服从 `single_runtime_owner`。

权威配置文件：

- `common/config/platform_capabilities.json`
