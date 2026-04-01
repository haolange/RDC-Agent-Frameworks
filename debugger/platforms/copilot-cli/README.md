# Copilot CLI 模板（平台模板）

<!-- BEGIN GENERATED COMMON-FIRST ADAPTER BLOCK -->
## Common-First Adapter Contract

- `common/` + package-local `tools/` 是 shared execution kernel；当前目录只保留宿主壳层。
- 当前平台的 `local_support`、`remote_support`、`enforcement_layer` 与 `coordination_mode` 统一以 `common/config/platform_capabilities.json` 为准。
- `adapter_readiness.json` 是当前适配就绪度记录，不是第二套运行规则。
<!-- END GENERATED COMMON-FIRST ADAPTER BLOCK -->

当前目录是 Copilot CLI 的 platform-local 模板。

入口规则：

- 默认入口是 local-first `CLI`；只有用户明确要求时才切换到 `MCP`
- 平台能力上限以 `common/config/platform_capabilities.json` 为准
- accepted intake 前必须同时具备可导入 `.rdc` 与 `strict_ready` 的 `fix reference`
- 缺少 `.rdc` 时阻断为 `BLOCKED_MISSING_CAPTURE`
- 缺少 fix reference 或只到 `fallback_only` 时阻断为 `BLOCKED_MISSING_FIX_REFERENCE`
- orchestrator 不得因为 specialist silence 或 timeout 抢做 live investigation

使用方式：

1. 覆盖 `common/`
2. 覆盖 `tools/`
3. 运行 `python common/config/validate_binding.py --strict`
4. 在当前平台根目录下使用 `workspace/`
