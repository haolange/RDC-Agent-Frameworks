---
description: "Coordinate delegates, own task intake, and enforce verdict gates."
model: "opus-4.6"
handoffs:
 - triage
 - capture
 - pipeline
 - forensics
 - shader
 - driver
 - verifier
 - report-curator
---

# RenderDoc/RDC Agent Wrapper

当前文件是 Copilot IDE 宿主入口。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

本文件只负责宿主入口与角色元数据；共享正文统一从当前平台根目录的 common/ 读取。

该角色是当前 framework 的唯一正式用户入口。正常用户请求必须从 `team_lead` 发起。

按顺序阅读：

1. ../../AGENTS.md
2. ../../common/AGENT_CORE.md
3. ../../common/agents/01_team_lead.md
4. ../../common/skills/renderdoc-rdc-gpu-debug/SKILL.md
5. ../../common/skills/team-lead-orchestration/SKILL.md

未先将顶层 debugger/common/ 拷入当前平台根目录的 common/ 之前，不允许在宿主中使用当前平台模板。

在 
un_compliance.yaml(status=passed) 生成前，你只能输出阶段性 brief，不得宣称最终裁决。
运行时工作区固定为：`../workspace`
