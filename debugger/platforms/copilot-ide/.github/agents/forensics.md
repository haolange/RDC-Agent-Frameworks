---
description: "Locate first bad event and pixel-level evidence."
model: "gpt-5"
handoffs:
  - orchestrator
---

# RenderDoc/RDC Agent Wrapper

当前文件是 Copilot IDE 宿主入口。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

本文件只引用共享 `common/` 正文，不得复制或改写角色职责。

按顺序阅读：

1. `../../../../common/AGENT_CORE.md`
2. `../../../../common/agents/05_pixel_value_forensics.md`
3. `../../../../common/skills/renderdoc-rdc-gpu-debug/SKILL.md`
