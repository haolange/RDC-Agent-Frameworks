# Codex 模板（平台模板）

## Common-First Adapter Contract

- `common/` + package-local `tools/` 是共享执行内核；平台目录只保留 adapter shell
- 目标 contract 统一来自 `common/config/platform_capabilities.json` 与 `common/config/framework_compliance.json`
- 当前平台 contract：`coordination_mode = staged_handoff`、`orchestration_mode = multi_agent`、`live_runtime_policy = single_runtime_single_context`
- shared harness / broker 是唯一 enforcement SSOT；`.codex/runtime_guard.py` 只是接入与转发入口
- live runtime 调用只能经 broker action；不允许临时 wrapper 封装 live CLI

当前目录是 Codex 的 workspace-native 模板。

入口规则：

- 默认入口是 local-first `CLI`；只有用户明确要求时才切换到 `MCP`
- `rdc-debugger` 是唯一 public entrypoint，但内部固定分为 `Plan / Intake Phase` 和 `Audited Execution Phase`
- Codex 若处于 Plan Mode，应先把用户请求收敛为 `debug_plan`
- 只有 `debug_plan.execution_readiness = ready` 时，execution 才能从 `entry_gate` 开始
- accepted intake 需要 `artifacts/entry_gate.yaml`、`artifacts/intake_gate.yaml`、`artifacts/runtime_session.yaml`、`artifacts/runtime_snapshot.yaml`、`artifacts/ownership_lease.yaml`、`artifacts/runtime_failure.yaml`
- capture import 与 case/run bootstrap 发生在 accepted intake 内，而不是在宿主外手工预放
- `triage + specialist + skeptic + curator` 必须走 sub-agent；控制面阶段仍由 guard/orchestrator 负责
- specialist silence、skeptic challenge、redispatch、timeout 都必须走 shared workflow，不得由 orchestrator 抢做 live investigation
