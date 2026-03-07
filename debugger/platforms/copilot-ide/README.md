# Copilot IDE Adaptation

这是面向 VS Code / IDE custom agents 的适配，不复刻 CLI plugin 布局。

## 完成态

- `.github/agents/`：完整角色集
- `.github/mcp.json`：MCP 入口
- `agent-plugin.json`：IDE 侧补充元数据
- `references/entrypoints.md`：知识入口与边界说明

## 宿主边界

- `preferred model` 仅表示偏好，不保证宿主一定采用
- hooks 在 IDE 宿主里以文档化边界形式处理，不伪造一个 CLI 风格 hooks 目录
- 不提供独立 `skills/` 目录；知识入口通过 agent 文档与 references 链接暴露
- framework 在该平台上的默认协作拓扑是 `staged_handoff`
- 即使有 custom agents，也不把同一 live session 当作多人并发工作区
- remote case 一律采用 `single_runtime_owner`
