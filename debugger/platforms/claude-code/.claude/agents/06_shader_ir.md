---
name: shader-ir
description: "Internal specialist for shader source, SPIR-V or IR evidence, and suspicious expression fingerprints. Use when a first_bad_event is bound to shader execution."
disallowedTools: Bash, Agent
model: "sonnet"
---

# RenderDoc/RDC Agent Wrapper（宿主入口）

当前文件是 Claude Code 宿主入口。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

本文件只负责宿主入口与角色元数据；共享正文统一从当前平台根目录的 `common/` 读取。

该角色默认是 internal/debug-only specialist。正常用户请求应先交给 `rdc-debugger` 完成 preflight 与路由，只有调试 framework 本身时才直接使用该角色。

按顺序阅读：

1. ../../AGENTS.md
2. ../../common/AGENT_CORE.md
3. ../../common/agents/06_shader_ir.md
4. ../../common/skills/rdc-debugger/SKILL.md
5. ../../common/skills/shader-ir/SKILL.md

未先将顶层 `debugger/common/` 拷入当前平台根目录的 `common/` 之前，不允许在宿主中使用当前平台模板。

运行时工作区固定为平台根目录下的 `workspace/`
