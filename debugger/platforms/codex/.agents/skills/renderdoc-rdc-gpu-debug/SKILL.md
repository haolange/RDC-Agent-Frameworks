# RenderDoc/RDC GPU Debug Skill Wrapper

当前文件是 Codex 的 skill 入口。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

共享 skill 入口：

- `../../../../../common/skills/renderdoc-rdc-gpu-debug/SKILL.md`
- `coordination_mode` 与降级边界以 `../../../../../common/config/platform_capabilities.json` 的当前平台定义为准。
