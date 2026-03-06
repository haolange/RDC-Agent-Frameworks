# Claude Work Entrypoints

本文件说明 `claude-work` 作为降级宿主时，Agent 应如何进入任务。

## 先读什么

1. `../../../common/AGENT_CORE.md`
2. `../../../docs/platform-capability-model.md`
3. `../../../docs/model-routing.md`
4. 若用户明确要求 `CLI` 模式：`../../../docs/cli-mode-reference.md`

## 降级原则

- 保留角色分工，不保留满配宿主的外壳能力假设。
- 若宿主缺少 hooks、skill 或 handoff 语义，Agent 仍必须遵守 artifact contract 与 skeptic signoff。
