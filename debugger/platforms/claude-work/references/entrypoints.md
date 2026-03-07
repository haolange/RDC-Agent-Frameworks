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
- 当前平台默认 `coordination_mode = staged_handoff`。
- live 调试时，sub agents 先提交 brief / evidence request，再由 runtime owner 执行工具链。
- local 若需要并行调查，只允许拆成多 `context/daemon` 链路。
- remote 一律使用 `single_runtime_owner`；其他角色不直接持有 live remote session。
- baton / rehydrate 规则以 `../../../docs/runtime-coordination-model.md` 为准。
