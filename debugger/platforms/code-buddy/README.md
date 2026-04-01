# Code Buddy 模板（平台模板）

<!-- BEGIN GENERATED COMMON-FIRST ADAPTER BLOCK -->
## Common-First Adapter Contract

- `common/` + package-local `tools/` are the shared execution kernel; platform folders are adapter shells.
- Host-visible native surfaces: `plugin`, `agents`, `skills`, `hooks`, `mcp`, `per_agent_model`
- Target contract comes from `common/config/platform_capabilities.json` and `common/config/framework_compliance.json`; it is not the same as current readiness.
- Current adapter must satisfy required surfaces: `agents`, `skills`, `hooks`, `mcp`
- Target contract: `coordination_mode = concurrent_team`, `sub_agent_mode = team_agents`, `peer_communication = direct`
- Current adapter readiness is tracked separately in `common/config/adapter_readiness.json`: `adapter_in_progress`
- `status_label` / `local_support` / `remote_support` / `enforcement_layer` describe repo posture only; they do not imply strict readiness.
- Strict execution must be enforced by shared harness, runtime lock, freeze state, artifact gate, and finalization receipt; not by prompt wording or host marketing text.
- Notes: Retains concurrent_team/team_agents/direct target contract; strict adapter must move beyond write-and-stop-only hooks.
<!-- END GENERATED COMMON-FIRST ADAPTER BLOCK -->


当前目录是 Code Buddy 的 platform-local 模板。

入口规则：

- 默认入口按 shared config 采用 local-first `CLI`
- 平台能力上限与宿主限制以 `common/config/platform_capabilities.json` 为准
- accepted intake 前必须同时具备可导入 `.rdc` 与 `strict_ready` 的 `fix reference`
- 缺少 `.rdc` 时阻断为 `BLOCKED_MISSING_CAPTURE`
- 缺少 fix reference 或只到 `fallback_only` 时阻断为 `BLOCKED_MISSING_FIX_REFERENCE`
- clarification、challenge、redispatch、timeout 必须遵循 shared workflow

使用方式：

1. 覆盖 `common/`
2. 覆盖 `tools/`
3. 运行 `python common/config/validate_binding.py --strict`
4. 在当前平台根目录下使用 `workspace/`
