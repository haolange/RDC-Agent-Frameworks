# RenderDoc/RDC GPU Debug（调试框架）

`debugger/` 是 `RDC-Agent-Frameworks` 中面向 RenderDoc/RDC GPU 调试场景的专属 framework 根目录。

这里定义 `debugger` 自己的运行前提、共享运行时文档入口、平台模板使用方式与维护者文档边界。仓库根文档不承接这些规则。

## 使用前提

开始使用 `debugger/` 之前，必须先完成：

1. 将仓库根目录 `debugger/common/` 整包拷贝到平台根目录的 `common/`。
2. 将 RDC-Agent-Tools 根目录整包拷贝到平台根目录的 `tools/`。
3. 确认 `tools/` 下存在 `validation.required_paths` 中列出的文件（README.md、docs/tools.md、docs/session-model.md、docs/agent-model.md、spec/tool_catalog.json）。
4. 运行 `python common/config/validate_binding.py --strict`，确认 `tools/`、snapshot 与宿主文档入口均已对齐。
5. 在当前对话提交至少一份 `.rdc`。

补充约束：

- `tools_root` 已固定为相对路径 `tools`；无需手动编辑 `platform_adapter.json`。
- source repo 中的 `tools/` 目录不存在，平台模板中的 `tools/` 默认为最小占位目录，用于 fail-closed；不要把 source repo 当成直接使用目标。

未完成以上步骤前：

- Agent 不得进入依赖平台真相的工作。
- 未提供 `.rdc` 时，Agent 必须以 `BLOCKED_MISSING_CAPTURE` 阻断，不得初始化 case/run 或继续调查。
- `README`、`AGENT_CORE`、skills 与平台模板都只能提供 framework 约束，不能替代 Tools 真相。

## 文档边界

- `common/AGENT_CORE.md`：`debugger` framework 的硬约束与运行原则。
- `common/docs/`：唯一运行时共享文档入口。
- `docs/`：仅服务 `debugger` 维护者的模板与 scaffold 说明，不是运行时共享资料区。

运行时共享文档入口：

- `common/AGENT_CORE.md`
- `common/docs/intake/README.md`
- `common/docs/cli-mode-reference.md`
- `common/docs/model-routing.md`
- `common/docs/platform-capability-matrix.md`
- `common/docs/platform-capability-model.md`
- `common/docs/runtime-coordination-model.md`
- `common/docs/truth_store_contract.md`
- `common/docs/workspace-layout.md`

维护者文档入口：

- `docs/README.md`
- `docs/多平台适配说明.md`

## 平台模板使用方式

平台模板位于 `platforms/<platform>/`。用户工作流：

1. 选择目标平台模板目录。
2. 将仓库根目录 `debugger/common/` 整包拷贝到该平台根的 `common/`。
3. 将 RDC-Agent-Tools 根目录整包拷贝到该平台根的 `tools/`。
4. 运行 `python common/config/validate_binding.py --strict`，确认 `tools/`、snapshot 与宿主文档入口都已对齐。
5. 完成覆盖后，在对应宿主中打开该平台根目录。
6. 正常用户请求从 `team_lead` 发起；其他 specialist 角色默认是 internal/debug-only。
7. 发起 debug 任务时，用户必须在当前对话提交一份或多份 `.rdc`。

说明：

- 平台内 `common/` 与 `tools/` 默认均只保留最小占位目录，用来等待整包覆盖。
- 未同时完成两项覆盖前，平台模板不可用。
- `tools_root` 已固定为相对路径 `tools`；无需手动编辑 `platform_adapter.json`。
- 平台入口选择必须遵循 shared docs 中的统一规则：可直达本地环境的宿主默认 local-first / daemon-backed `CLI`，不能直达本地环境的宿主默认 `MCP`。
- 任务开始时，Agent 必须向用户说明当前采用的入口模式；若所选入口的前置条件未满足，必须先阻断。
- 缺少 `.rdc` 时，Agent 必须像 `tools_root` 未配置一样直接阻断，不得继续做 triage、investigation 或 planning。
- 当前 snapshot 需要与 `RDC-Agent-Tools` 的 `202` 个 tools 对齐；其中新增的 `rd.vfs.*` 只读探索面与 tabular projection 能力都属于必须同步校验的 platform truth。
- 当前已实测闭环的是 package-level manual binding 与 local-first 工具链；remote workflow 本轮未重新验证，不应在 framework 文档中写成“已验证”。
