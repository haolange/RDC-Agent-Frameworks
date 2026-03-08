---
agent_id: "curator_agent"
category: "reporter"
model: "gemini-3.1-pro"
delegates_to:
  - team_lead
---

# RenderDoc/RDC Agent Wrapper

当前文件是 Code Buddy 宿主入口。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

本文件只引用共享 `common/` 正文，不得复制或改写角色职责。

按顺序阅读：

1. `../../../common/AGENT_CORE.md`
2. `../../../common/agents/09_report_knowledge_curator.md`
3. `../../../common/skills/renderdoc-rdc-gpu-debug/SKILL.md`
