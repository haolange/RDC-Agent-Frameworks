# Claude Code 模板（平台模板）

<!-- BEGIN GENERATED COMMON-FIRST ADAPTER BLOCK -->
## Common-First Adapter Contract

- `common/` + package-local `tools/` are the shared execution kernel; platform folders are adapter shells.
- Host-visible native surfaces: `agents`, `skills`, `hooks`, `mcp`, `per_agent_model`
- Target contract comes from `common/config/platform_capabilities.json` and `common/config/framework_compliance.json`; it is not the same as current readiness.
- Current adapter must satisfy required surfaces: `agents`, `skills`, `hooks`, `mcp`
- Target contract: `coordination_mode = concurrent_team`, `sub_agent_mode = team_agents`, `peer_communication = direct`
- Current adapter readiness is tracked separately in `common/config/adapter_readiness.json`: `adapter_in_progress`
- `status_label` / `local_support` / `remote_support` / `enforcement_layer` describe repo posture only; they do not imply strict readiness.
- Strict execution must be enforced by shared harness, runtime lock, freeze state, artifact gate, and finalization receipt; not by prompt wording or host marketing text.
- Notes: Retains concurrent_team/team_agents/direct target contract; strict adapter depends on shared harness and host hook wiring.
<!-- END GENERATED COMMON-FIRST ADAPTER BLOCK -->


当前目录是 Claude Code 的 platform-local 模板。

入口规则：

- 默认入口是 daemon-backed `CLI`；只有用户明确要求时才切换到 `MCP`
- 平台能力上限、协作模式与 hooks 分层以 `common/config/platform_capabilities.json` 为准
- accepted intake 需要 `artifacts/entry_gate.yaml` 与 `artifacts/runtime_topology.yaml`
- accepted intake 前必须同时具备可导入 `.rdc` 与 `strict_ready` 的 `fix reference`
- 缺少 `.rdc` 时阻断为 `BLOCKED_MISSING_CAPTURE`
- 缺少 fix reference 或只到 `fallback_only` 时阻断为 `BLOCKED_MISSING_FIX_REFERENCE`
- triage clarification、skeptic challenge、redispatch、timeout 都必须走 shared workflow，不得静默兜底

使用方式：

1. 覆盖 `common/`
2. 覆盖 `tools/`
3. 运行 `python common/config/validate_binding.py --strict`
4. 在当前平台根目录下使用 `workspace/`

平台说明：

- 这里只保留 Claude Code 壳层说明；流程真相以 shared `common/` 为准
- reopen / reconnect 产生新的 `session_id` / `context_id` 是预期行为
