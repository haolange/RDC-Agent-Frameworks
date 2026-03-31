# Code Buddy 模板（平台模板）

<!-- BEGIN GENERATED COMMON-FIRST ADAPTER BLOCK -->
## Common-First Adapter Contract

- `common/` + package-local `tools/` 是共享执行内核，platform folder 只是 adapter 壳层。
- 宿主可见的 native surface：`plugin`、`agents`、`skills`、`hooks`、`mcp`、`per_agent_model`。
- 目标合同来自 `common/config/platform_capabilities.json` 和 `common/config/framework_compliance.json`，不等同于当前 readiness。
- 当前 adapter 必须满足的 surface：`agents`、`skills`、`hooks`、`mcp`。
- 目标合同：`coordination_mode = concurrent_team`、`sub_agent_mode = team_agents`、`peer_communication = direct`。
- 当前 adapter readiness 单独记录在 `common/config/adapter_readiness.json`：`adapter_in_progress`。
- `status_label` / `local_support` / `remote_support` / `enforcement_layer` 只描述仓库姿态，不代表 strict readiness。
- 严格执行必须由 shared harness、runtime lock、freeze state、artifact gate 和 finalization receipt 共同约束。
<!-- END GENERATED COMMON-FIRST ADAPTER BLOCK -->

当前目录是 Code Buddy 的 platform-local 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

入口规则：

- 当前宿主可直接访问本地进程、文件系统与 workspace，默认采用 local-first。
- 默认入口是 daemon-backed `CLI`；只有用户明确要求按 `MCP` 接入时，才切换到 `MCP`。
- 任务开始时，Agent 必须向用户说明当前采用的是 `CLI` 还是 `MCP`。
- 当前模板默认不预注册 MCP；若要启用，使用 `.mcp.opt-in.json` 的示例配置显式接入。

使用方式：

1. 将 `debugger/common/` 拷贝到当前平台根目录的 `common/`。
2. 将 `RDC-Agent-Tools` 根目录拷贝到当前平台根目录的 `tools/`。
3. 运行 `python common/config/validate_binding.py --strict`。
4. 使用当前平台根目录下的 `workspace/` 作为运行区。
5. 平台启动后默认保持普通对话态；只有用户手动召唤 `rdc-debugger`，才进入调试框架。

约束：

- `common/` 只保留一个占位文件；正式共享正文仍由顶层 `debugger/common/` 提供。
- 未完成 `debugger/common/` 覆盖前，当前平台模板不可用。
- 未完成 `debugger/common/` 覆盖、`tools/` 覆盖或 binding 校验前，Agent 必须拒绝执行依赖平台真相的工作。
- 当前工具 snapshot 必须与 `RDC-Agent-Tools` 当前 catalog 完整对齐，并覆盖 `rd.vfs.*`、`rd.session.*`、`rd.core.*`。
- 未提供可导入的 `.rdc` 时，Agent 必须以 `BLOCKED_MISSING_CAPTURE` 直接阻断。
- 当前平台按 `pseudo-hooks` 处理；`hooks/hooks.json` 只作为 wrapper 触发面。
- 结案仍必须依赖共享 harness 与 `artifacts/run_compliance.yaml`。
