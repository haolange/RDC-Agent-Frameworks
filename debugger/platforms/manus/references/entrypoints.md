# Manus Entrypoints

本文件说明 `manus` 作为 workflow 宿主时的最小入口。

## 先读什么

1. `../../../common/AGENT_CORE.md`
2. `../../../docs/platform-capability-model.md`
3. `../../../docs/model-routing.md`

## workflow 入口

- 把 Manus 理解成阶段化执行器，而不是多 Agent 满配宿主。
- 当前平台默认 `coordination_mode = workflow_stage`。
- remote 阶段只允许单一 runtime owner 顺序执行 `connect -> open_replay -> re-anchor -> collect evidence`。
- 进入任务时，先确认 session artifact contract，再决定是否继续 workflow。
- 若任务需要动态 tool discovery、多 agent handoff、多个 live owners 或细粒度模型绑定，应切回更高能力的平台适配。
- baton / rehydrate 规则以 `../../../docs/runtime-coordination-model.md` 为准。
