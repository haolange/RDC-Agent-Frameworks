# Manus Workspace Instructions

当前目录是 Manus 的 platform-local 模板。所有角色在进入 role-specific 行为前，都必须先服从本文件与共享 common/ 约束。

先阅读：

1. common/AGENT_CORE.md
2. common/config/platform_adapter.json
3. common/skills/renderdoc-rdc-gpu-debug/SKILL.md
4. common/docs/platform-capability-model.md
5. common/docs/model-routing.md

强制规则：

- 正常用户入口只有 `team_lead`
- 其他 specialist 默认是 internal/debug-only，由 `team_lead` 决定是否分派
- `platform_adapter.json` 未配置或 `tools_root` 校验失败时，必须立即停止，不得继续做依赖平台真相的工作

未先将顶层 debugger/common/ 拷入当前平台根目录的 common/ 之前，不允许在宿主中使用当前平台模板。

运行时工作区固定为：`../workspace`
- 当前宿主按 workflow_stage 降级运行；最终仍必须生成 rtifacts/run_compliance.yaml 才算合规结案。
- 不得在该宿主上模拟实时 multi-agent handoff。
