---
name: plan-compiler
description: "Internal planning sub-agent for compiling the final debug_plan handoff."
tools: Read, Grep, Glob, Write, Edit
model: "opus"
---

# RenderDoc/RDC Agent 宿主入口

当前文件是 Claude Code 宿主入口。

该角色属于 `Plan / Intake Phase` 的轻量 planning sub-agent。它只编译 `debug_plan`，不进入 execution。
