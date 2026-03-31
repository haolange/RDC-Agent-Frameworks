# Copilot CLI Template（平台模板）

当前目录是 Copilot CLI 的 platform-local 模板，目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

入口规则：

- 当前宿主可直接访问本地进程、文件系统与 workspace，默认采用 local-first。
- 默认入口是 daemon-backed `CLI`；只有用户明确要求按 `MCP` 接入时，才切换到 `MCP`。
- 任务开始时，Agent 必须先向用户说明当前采用的是 `CLI` 还是 `MCP`。
- 如果用户要求 `MCP`，但宿主未配置对应 `MCP server`，必须直接阻断并提示配置。
- 当前模板默认不预注册 `MCP`；若要启用，使用 `.mcp.opt-in.json` 的示例配置显式接入。

使用方式：

1. 将仓库根目录 `debugger/common/` 整体拷贝到当前平台根目录的 `common/`，覆盖占位内容。
2. 将 `RDC-Agent-Tools` 根目录整包拷贝到当前平台根目录的 `tools/`，覆盖占位内容。
3. 确认 `tools/` 下存在 `validation.required_paths` 列出的必需文件，并确认 `rdx.bat` 与 bundled runtime 已随包覆盖。
4. 运行 `python common/config/validate_binding.py --strict`，确认 package-local `tools/`、zero-install runtime、snapshot、宿主入口文件与共享文档全部对齐。
5. 正式发起 debug 前，用户必须先提供至少一份 `.rdc`；可在当前对话上传，或提供宿主当前会话可访问的文件路径。accepted intake 后由 Agent 导入 `workspace/cases/<case_id>/inputs/captures/`。
6. 使用当前平台根目录下、与 `common/` 和 `tools/` 并列的 `workspace/` 作为运行区。
7. 完成覆盖后，再在对应宿主中打开当前平台根目录。
8. 平台启动后默认保持普通对话态；只有用户手动召唤 `rdc-debugger`，才进入调试框架。除 `rdc-debugger` 之外，其他 specialist 默认都是 internal/debug-only。

约束：

- `common/` 默认只保留一个占位文件；正式共享正文仍由顶层 `debugger/common/` 提供，并由用户显式拷入。
- 未完成 `debugger/common/` 覆盖前，当前平台模板不可用。
- 未完成 `debugger/common/` 覆盖、`tools/` 覆盖或 binding 校验前，Agent 必须拒绝执行依赖平台真相的工作。
- 当前工具 snapshot 必须与 `RDC-Agent-Tools` 当前 catalog 完整对齐，并覆盖 `rd.vfs.*` 导航层、扩展 `rd.session.*`、`rd.core.*` discovery/observability，以及 bounded event-tree 读取语义；其中 `tabular/tsv` 仅作为 projection 支持。
- 当前平台属于 `native-hooks` tier；`hooks/hooks.json` 只负责触发共享 dispatcher 和 `common/hooks/utils/harness_guard.py`，不在平台侧复制业务规则。
- `native hooks` 会拦截 `session_start` / `pre_tool_use` / `post_tool_use` / `stop`，同时仍以 `artifacts/run_compliance.yaml` 作为统一合规裁决。