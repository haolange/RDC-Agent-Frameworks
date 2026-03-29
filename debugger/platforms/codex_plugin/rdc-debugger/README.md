# Codex Plugin Bundle（插件包）

当前目录是 Codex 的 installable plugin bundle。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

入口规则：

- 当前宿主可直接访问本地进程、文件系统与 workspace，默认采用 local-first。
- 默认入口是 daemon-backed `CLI`；只有用户明确要求按 `MCP` 接入且已手动启用 `references/mcp-opt-in.sample.toml` 中的配置片段时，才切换到 `MCP`。
- 任务开始时，Agent 必须向用户说明当前采用的是 `CLI` 还是 `MCP`。
- 若用户要求 `MCP`，但宿主尚未按 sample 配置对应 server，必须直接阻断并提示配置。
- 当前插件不会在 manifest 中默认预注册 MCP；`MCP` 只通过文档化 opt-in 提供。
- 当前平台的 `local_support` / `remote_support` / `enforcement_layer` 以 `common/config/platform_capabilities.json` 中 `codex_plugin` 行为准。

使用方式：

1. 将仓库根目录 `debugger/common/` 整体拷贝到当前插件根目录的 `common/`，覆盖占位内容。
2. 将 `RDC-Agent-Tools` 根目录整包拷贝到当前插件根目录的 `tools/`，覆盖占位内容。
3. 确认 `tools/` 下存在 `validation.required_paths` 列出的必需文件。
4. 运行 `python common/config/validate_binding.py --strict`，确认 package-local `tools/`、snapshot、共享文档与插件包根目录全部对齐。
5. 使用当前插件根目录下、与 `common/` 和 `tools/` 并列的 `workspace/` 作为运行区。
6. 将当前目录同步到 `~/.agents/plugins/rdc-debugger/`。
7. 将 `../references/personal-marketplace.sample.json` 合并到 `~/.agents/plugins/marketplace.json`。
8. 在 Codex 中打开 `/plugins` 安装或刷新 `rdc-debugger`。
9. 平台启动后默认保持普通对话态；只有用户手动召唤 `rdc-debugger`，才进入调试框架。除 `rdc-debugger` 之外，其他 specialist 默认都是 internal/debug-only。

约束：

- `common/` 默认只保留一个占位文件；正式共享正文仍由顶层 `debugger/common/` 提供，并由用户显式拷入。
- 未完成 `debugger/common/` 覆盖、`tools/` 覆盖或 binding 校验前，Agent 必须拒绝执行依赖平台真相的工作。
- 未提供可导入的 `.rdc` 时，Agent 必须以 `BLOCKED_MISSING_CAPTURE` 直接阻断，不得初始化 case/run 或继续 triage、investigation、planning。
- 当前插件不依赖 `.codex/config.toml` 或 `.codex/agents/*.toml`；specialist 角色通过安装型 `skills/` 提供，并由 `rdc-debugger` 显式要求 Codex 创建通用 sub-agent 后加载。
- 当前工具 snapshot 必须与 `RDC-Agent-Tools` 当前 catalog 完整对齐，并覆盖 `rd.vfs.*` 导航层、扩展 `rd.session.*`、`rd.core.*` discovery/observability，以及 bounded event-tree 读取语义；其中 `tabular/tsv` 仅作为 projection 支持。
- 本地 plugin 安装后实际运行的是 Codex cache 副本，而不是 source repo 当前目录；每次重新覆盖 `common/` 或 `tools/` 后，都必须重新同步 `~/.agents/plugins/rdc-debugger/`，再在 `/plugins` 中刷新或重装。
