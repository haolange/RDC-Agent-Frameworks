# Codex Workspace Instructions

当前目录是 Codex workspace-native 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

先阅读：

1. `../../common/AGENT_CORE.md`
2. `../../common/skills/renderdoc-rdc-gpu-debug/SKILL.md`
3. `../../common/docs/platform-capability-model.md`
4. `../../common/docs/model-routing.md`

角色约束：

- `team_lead` 负责分派和结案门槛，不直接执行 live 调试。
- 专家角色的共享 prompt 真相保存在 `../../common/agents/*.md`；`.codex/agents/*.toml` 只负责模型、reasoning、verbosity 与 sandbox。
- remote case 继续服从 `single_runtime_owner`，不得因为 `multi_agent` 就共享 live runtime。
