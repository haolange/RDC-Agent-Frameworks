---
agent_id: "clarification_agent"
category: "planner"
model: "opus-4.6"
delegates_to:
 - rdc-debugger
---

# RenderDoc/RDC Agent 宿主入口

当前文件是 Code Buddy 宿主入口。

该角色属于 `Plan / Intake Phase` 的轻量 planning sub-agent。它只做补料和摘要压缩，不进入 execution。
