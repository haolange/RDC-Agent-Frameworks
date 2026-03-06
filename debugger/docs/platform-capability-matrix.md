# Platform Capability Matrix

本文按宿主平台能力定义各平台适配的“最佳实现上限”，并与 `common/config/platform_capabilities.json` 保持一致。

| Platform | Custom Agents/Subagents | Skills | Hooks | MCP | Per-Agent Model | Nested Delegation / Handoffs | Packaging |
|---|---|---|---|---|---|---|---|
| Code Buddy | Yes | Yes | Yes | Yes | Explicit | Yes | Plugin bundle |
| Claude Code | Yes | Yes | Yes | Yes | Alias-level | Yes | Project config + subagents |
| Copilot CLI | Yes | Yes | Yes | Yes | Inherit-first | Limited | CLI plugin |
| Copilot IDE | Yes | No first-class skill layer | Documented boundary | Yes | Preferred | Yes | `.github/agents` + MCP |
| Claude Work | Yes | No first-class skill layer | No | Yes | Inherit | Weak | Local plugin contract |
| Manus | Workflow-level only | No | No | No | Workflow-level | Workflow-level | Workflow package |

## 解释

- `Code Buddy` 是当前最高完成度参考实现。
- `Claude Code` 必须具备 `subagents + hooks + MCP + model alias` 的真实落地文件。
- `Copilot CLI` 保持 plugin 形态，但 `CLI` 模式下禁止 discovery-by-trial-and-error。
- `Copilot IDE` 应使用 `.github/agents`、MCP、preferred model 与文档化边界，不伪造 CLI skill 目录。
- `Claude Work` 与 `Manus` 仅作为降级适配，不伪装成满配宿主。

权威配置文件：

- `common/config/platform_capabilities.json`
