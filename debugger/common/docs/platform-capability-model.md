# 平台能力模型

本文解释 `common/config/platform_capabilities.json` 的语义模型。JSON 是唯一权威源；本文只负责把字段含义展开为维护者可读说明。

## 核心区分

- `sub agent 支持不等于 team agents`。平台可以支持 sub agents，但这不自动意味着 specialist 之间拥有 peer-to-peer 通信能力。
- `team_agents` 表示 specialist 可以直接通信并共享 host-level delegation surface。
- `puppet_sub_agents` 表示 specialist 角色存在，但所有 brief、冲突与下一轮 dispatch 都必须经主入口中转。
- `instruction_only_sub_agents` 表示宿主只能在 spawn 时注入 instruction，不承载独立 agent 描述文件。

## 协调模式

- `staged_handoff` 是 `hub-and-spoke` 多轮接力：主入口先做 gate，再分派 specialist，收 brief 后继续推进。
- `workflow_stage` 是串行 workflow，不是实时 multi-agent handoff。
- local 下的 `multi_context_orchestrated` 只表示 shared harness 可以协调多个 specialist context，不代表宿主原生提供 concurrent team enforcement。
- remote 一律以 `single_runtime_owner` 为真相：即便平台支持多 specialist，多 live remote owner 也不被视为正式能力。
- `serial_only` 说明 remote 只能以串行 workflow / 单 owner 方式推进，不允许把 local 并行 ceiling 直接投射到 remote。

## Enforcement 分级

- `native-hooks`：宿主能用原生 lifecycle hooks 触发 shared harness。
- `pseudo-hooks`：宿主只能用 wrapper / rules / runtime guard 伪造严格 hooks。
- `no-hooks`：宿主无法可靠 host-side 拦截，只能依赖 shared harness + final audit。

## Public Entrypoint

- `rdc-debugger` 是所有平台唯一 public entrypoint。
- 其它 specialist 默认 internal-only；平台可以暴露它们的文件或 wrapper，但不能把它们当作用户默认入口。
