# Claude Desktop Template（平台模板）

当前目录是 Claude Desktop 的 platform-local 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

入口规则：

- 当前宿主不支持独立 custom agent 描述文件与 native hooks，但当前模板仍提供 wrapper skills 来统一入口语义。
- 当前平台只允许通过 `MCP` 进入平台真相，不允许尝试 `CLI`。
- 任务开始时，Agent 必须向用户说明当前采用的是 `MCP`，并先完成 MCP preflight。
- 用户提供可导入的 `.rdc` 后，按 `workflow_stage` 串行 specialist 流推进；当前平台支持 instruction-only sub agents，但不支持实时 team-agent handoff。
- 当前平台的 `sub_agent_mode = instruction_only_sub_agents`；如需子 agent，只能由主 agent 在实例化时注入 instruction，而不是依赖独立 agent 描述文件。
- 当前模板默认不预注册 MCP；启用时应显式填充 `claude_desktop_config.opt-in.json` 的示例配置。
- 当前平台的 `local_support` / `remote_support` / `enforcement_layer` 以 `common/config/platform_capabilities.json` 中 `claude-desktop` 行为准。

使用方式：

1. 将仓库根目录 `debugger/common/` 整体拷贝到当前平台根目录的 `common/`，覆盖占位内容。
2. 将 `RDC-Agent-Tools` 根目录整包拷贝到当前平台根目录的 `tools/`，覆盖占位内容。
3. 确认 `tools/` 下存在 `validation.required_paths` 列出的必需文件，并确认零安装入口 `rdx.bat` 与 bundled runtime 已随包覆盖。
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
- 未提供可导入的 `.rdc` 时，Agent 必须以 `BLOCKED_MISSING_CAPTURE` 直接阻断，不得初始化 case/run 或继续 triage、investigation、planning。
- `workspace/` 预生成空骨架；真实运行产物在平台使用阶段按 case/run 写入。
- 维护者若重跑 scaffold，必须继续产出 platform-local `common/` 最小占位目录，不得回退到跨级引用。
- 当前平台属于 `no-hooks` tier；宿主按 `workflow_stage` 串行运行，不能伪造 host-side strict hooks。最终仍必须生成 `artifacts/run_compliance.yaml` 才算合规结案。
- 可进行串行 specialist dispatch，但不得在该宿主上模拟实时 multi-agent handoff。
- 不得把独立 specialist 描述文件误写成 Claude Desktop 宿主能力；该宿主只支持 spawn-time instruction。
- 用户侧 capture intake 支持当前对话上传 `.rdc` 或提供宿主当前会话可访问的文件路径；平台模板只负责把导入后的 case/run 现场写入 `workspace/`。
