# Codex 模板（平台模板）

<!-- BEGIN GENERATED COMMON-FIRST ADAPTER BLOCK -->
## Common-First Adapter Contract

- `common/` + package-local `tools/` are the shared execution kernel; platform folders are adapter shells.
- Host-visible native surfaces: `workspace_instructions`, `skills`, `mcp`, `per_role_config`, `multi_agent`
- Target contract comes from `common/config/platform_capabilities.json` and `common/config/framework_compliance.json`; it is not the same as current readiness.
- Current adapter must satisfy required surfaces: `agents`, `skills`, `mcp`
- Target contract: `coordination_mode = staged_handoff`, `sub_agent_mode = puppet_sub_agents`, `peer_communication = via_main_agent`
- Current adapter readiness is tracked separately in `common/config/adapter_readiness.json`: `adapter_in_progress`
- `status_label` / `local_support` / `remote_support` / `enforcement_layer` describe repo posture only; they do not imply strict readiness.
- Strict execution must be enforced by shared harness, runtime lock, freeze state, artifact gate, and finalization receipt; not by prompt wording or host marketing text.
- Notes: Wave 1 strict target using runtime_guard plus common-first control interfaces.
<!-- END GENERATED COMMON-FIRST ADAPTER BLOCK -->


当前目录是 Codex 的 workspace-native 模板。

入口规则：

- 默认入口是 local-first `CLI`；只有用户明确要求时才切换到 `MCP`
- 平台能力上限与协作模式以 `common/config/platform_capabilities.json` 为准
- 当前平台通过 `runtime_owner + shared harness guard + audit artifacts` 执行强门禁
- `.codex/runtime_guard.py` 是 Codex 平台的 enforcement entrypoint
- accepted intake 需要 `artifacts/entry_gate.yaml`、`artifacts/intake_gate.yaml`、`artifacts/runtime_topology.yaml`
- capture import 与 case/run bootstrap 发生在 accepted intake 内，而不是在宿主外手工预放
- accepted intake 前必须同时具备可导入 `.rdc` 与 `strict_ready` 的 `fix reference`
- 缺少 `.rdc` 时阻断为 `BLOCKED_MISSING_CAPTURE`
- 缺少 fix reference 或只到 `fallback_only` 时阻断为 `BLOCKED_MISSING_FIX_REFERENCE`
- specialist silence、skeptic challenge、redispatch、timeout 都必须走 shared workflow，不得由 orchestrator 抢做 live investigation

使用方式：

1. 覆盖 `common/`
2. 覆盖 `tools/`
3. 运行 `python common/config/validate_binding.py --strict`
4. 在当前平台根目录下使用 `workspace/`

平台说明：

- 这里只保留宿主壳层说明；流程真相以 shared `common/` 为准
- reopen / reconnect 产生新的 `session_id` / `context_id` 是预期行为
