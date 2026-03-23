# Claude Code Template（平台模板）

当前目录是 Claude Code 的 platform-local 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

使用方式：

1. 将仓库根目录 `debugger/common/` 整体拷贝到当前平台根目录的 `common/`，覆盖占位内容。
2. 将 `RDC-Agent-Tools` 根目录整包拷贝到当前平台根目录的 `tools/`，覆盖占位内容。
3. 确认 `tools/` 下存在 `validation.required_paths` 列出的必需文件。
4. 运行 `python common/config/validate_binding.py --strict`，确认 package-local `tools/`、snapshot、宿主入口文件与共享文档全部对齐。
5. 正式发起 debug 前，用户必须在当前对话提交至少一份 `.rdc`。
6. 使用当前平台根目录同级的 `workspace/` 作为运行区。
7. 完成覆盖后，再在对应宿主中打开当前平台根目录。
8. Claude Code 的正式用户入口固定为 `.claude/settings.json` 中的 session-wide `team-lead` agent；其他 specialist 默认是 internal/debug-only。

约束：

- `common/` 默认只保留一个占位文件；正式共享正文仍由顶层 `debugger/common/` 提供，并由用户显式拷入。
- 覆盖完成后，平台根 `common/README.md` 会成为正式 shared common 的入口说明，不再保留占位语义。
- 未完成 `debugger/common/` 覆盖前，当前平台模板不可用。
- 未完成 `debugger/common/` 覆盖、`tools/` 覆盖或 binding 校验前，Agent 必须拒绝执行依赖平台真相的工作。
- 当前工具 snapshot 必须与 `RDC-Agent-Tools` 当前 catalog 完整对齐，并覆盖 `rd.vfs.*` 导航层、扩展 `rd.session.*`、`rd.core.*` discovery/observability，以及 bounded event-tree 读取语义；其中 `tabular/tsv` 仅作为 projection 支持。
- Claude hooks 使用 string `matcher`；文件路径过滤由共享 hook dispatcher 读取 hook payload 后自行判断，不在 settings.json 里写 object matcher。
- Claude Code 的 live RenderDoc 访问统一走已配置的 MCP server；不要把 `python ...run_cli.py` 一类 Bash 包装当成正常路径。
- 未提供 `.rdc` 时，Agent 必须以 `BLOCKED_MISSING_CAPTURE` 直接阻断，不得初始化 case/run 或继续 triage、investigation、planning。
- `workspace/` 预生成空骨架；真实运行产物在平台使用阶段按 case/run 写入。
- 维护者若重跑 scaffold，必须继续产出 platform-local `common/` 最小占位目录，不得回退到跨级引用。
- native hooks 会阻断未通过 gate 的结案；同时仍要求生成 `artifacts/run_compliance.yaml` 作为统一合规裁决。
