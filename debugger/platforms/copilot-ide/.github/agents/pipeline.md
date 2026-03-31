---
description: "Trace pass divergence and resource dependency chains."
model: "sonnet-4.6"
handoffs:
 - orchestrator
---

# RenderDoc/RDC Agent 宿主入口

当前文件是 Copilot IDE 宿主入口。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

本文件只负责宿主入口与角色元数据；共享正文统一从当前平台根目录的 `common/` 读取。

该角色默认是 internal/debug-only specialist。平台启动后不会自动进入该角色；只有用户手动召唤 `rdc-debugger` 并由它完成分派时，才进入当前 role。

按顺序阅读：

1. ../../AGENTS.md
2. ../../common/AGENT_CORE.md
3. ../../common/agents/04_pass_graph_pipeline.md
4. ../../common/skills/rdc-debugger/SKILL.md
5. ../../common/skills/pass-graph-pipeline/SKILL.md

未先将顶层 `debugger/common/` 拷入当前平台根目录的 `common/` 之前，不允许在宿主中使用当前平台模板。

运行时工作区固定为平台根目录下的 `workspace/`
