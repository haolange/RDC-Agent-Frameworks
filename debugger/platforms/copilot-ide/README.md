# Copilot IDE Template

当前目录是 Copilot IDE 的 direct-reference workspace 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

约束：

- 本目录直接引用仓库中的共享 `debugger/common/`，禁止复制或镜像 `common/` 内容。
- 当前平台状态：`full`。
- 当前平台生成面：`agents, skills, mcp, preferred_model, handoffs`。
- 共享模型、delegation、hook、MCP 与入口布局全部来自 `common/config/` 和 `debugger/scripts/sync_platform_scaffolds.py`。
