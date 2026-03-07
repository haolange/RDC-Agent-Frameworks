# Copilot IDE Entrypoints

本文件是 `copilot-ide` 的知识入口，不是 skill 替代品。

## 先读什么

1. `../../../common/AGENT_CORE.md`
2. `../../../docs/platform-capability-model.md`
3. `../../../docs/platform-capability-matrix.md`
4. `../../../docs/model-routing.md`
5. 若用户要求 `CLI` 模式：`../../../docs/cli-mode-reference.md`

## 使用规则

- 在 IDE 宿主里，优先通过 MCP 与 custom agents 进行任务分派。
- 当前平台默认 `coordination_mode = staged_handoff`：sub agents 先提交 brief，再由 runtime owner 执行 live 工具链。
- local 若需要并行调查，只允许拆成多 `context/daemon` 链路，不允许多个 Agent 共享同一 live session。
- remote 一律使用 `single_runtime_owner`；其他专家角色只提交 brief / evidence request。
- 不要在 IDE 里模拟 Copilot CLI 的命令探索流程。
- 如果用户明确要求 `CLI` 模式，应把它视为受约束参考流程，而不是在 IDE 终端里自行试错。
- baton / rehydrate 规则以 `../../../docs/runtime-coordination-model.md` 为准。
