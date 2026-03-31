# Copilot IDE Template（平台模板）

<!-- BEGIN GENERATED COMMON-FIRST ADAPTER BLOCK -->
## Common-First Adapter Contract

- `common/` + package-local `tools/` 是共享执行内核；平台目录只是 adapter 壳层。
- 宿主可见的原生面：`agents`、`skills`、`mcp`、`preferred_model`、`handoffs`
- 目标合同来自 `common/config/platform_capabilities.json` 和 `common/config/framework_compliance.json`；它不等于当前 readiness。
- 当前 adapter 必须满足的 surface：`agents`、`skills`、`mcp`
- 目标合同：`coordination_mode = staged_handoff`、`sub_agent_mode = puppet_sub_agents`、`peer_communication = via_main_agent`
- 当前 adapter readiness 由 `common/config/adapter_readiness.json` 单独跟踪：`adapter_in_progress`
- `status_label` / `local_support` / `remote_support` / `enforcement_layer` 只描述仓库姿态，不代表 strict readiness。
- 严格执行必须依赖 shared harness、runtime lock、freeze state、artifact gate 和 finalization receipt，而不是 prompt wording 或宿主宣传文案。
- 说明：Wave 1 的 strict 目标通过外部 common-first enforcement 实现，不假定 IDE 原生 hard hooks。
<!-- END GENERATED COMMON-FIRST ADAPTER BLOCK -->

当前目录是 Copilot IDE 的 platform-local 模板，目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

入口规则：

- 当前宿主可直接访问本地进程、文件系统与 workspace，默认采用 local-first。
- 默认入口是 daemon-backed `CLI`；只有用户明确要求按 `MCP` 接入时，才切换到 `MCP`。
- 任务开始时，Agent 必须先向用户说明当前采用的是 `CLI` 还是 `MCP`。
- 如果用户要求 `MCP`，但宿主未配置对应 `MCP server`，必须直接阻断并提示配置。
- 当前模板默认不预注册 `MCP`；若要启用，使用 `.github/mcp.opt-in.json` 的示例配置显式接入。

使用方式：

1. 将仓库根目录 `debugger/common/` 整体拷贝到当前平台根目录的 `common/`，覆盖占位内容。
2. 将 `RDC-Agent-Tools` 根目录整包拷贝到当前平台根目录的 `tools/`，覆盖占位内容。
3. 确认 `tools/` 下存在 `validation.required_paths` 列出的必需文件，并确认 `rdx.bat` 与 bundled runtime 已随包覆盖。
4. 运行 `python common/config/validate_binding.py --strict`，确认 package-local `tools/`、zero-install runtime、snapshot、宿主入口文件与共享文档全部对齐。
5. 正式发起 debug 前，用户必须先提供至少一份 `.rdc`；可在当前对话上传，或提供宿主当前会话可访问的文件路径。accepted intake 后由 Agent 导入 `workspace/cases/<case_id>/inputs/captures/`。
6. 使用当前平台根目录下、与 `common/` 和 `tools/` 并列的 `workspace/` 作为运行区。
7. 完成覆盖后，再在对应宿主中打开当前平台根目录。
8. 平台启动后默认保持普通对话态；只有用户手动召唤 `rdc-debugger`，才进入调试框架。除 `rdc-debugger` 之外，其他 specialist 默认都是 internal/debug-only。