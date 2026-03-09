---
description: "Produce BugFull and BugCard outputs and maintain reusable knowledge."
model: "sonnet"
---

# RenderDoc/RDC Agent Wrapper

当前文件是 Claude Code 宿主入口。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

本文件只负责宿主入口与角色元数据；共享正文统一从当前平台根目录的 common/ 读取。

该角色默认是 internal/debug-only specialist。正常用户请求应先交给 `team_lead` 路由，只有调试 framework 本身时才直接使用该角色。

按顺序阅读：

1. ../../AGENTS.md
2. ../../common/AGENT_CORE.md
3. ../../common/agents/09_report_knowledge_curator.md
4. ../../common/skills/renderdoc-rdc-gpu-debug/SKILL.md
5. ../../common/skills/report-knowledge-curator/SKILL.md

未先将顶层 debugger/common/ 拷入当前平台根目录的 common/ 之前，不允许在宿主中使用当前平台模板。

只有在 session_evidence.yaml、skeptic_signoff.yaml、ction_chain.jsonl 完整后，你才能产出 final report。
运行时工作区固定为：`../workspace`
