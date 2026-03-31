# Manus 模板（平台模板）

当前目录是 Manus 的 platform-local 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

入口规则：

- 当前宿主按 workflow package 运行，协作上限仍是 `workflow_stage`。
- 当前平台只允许 `MCP` 作为工具入口，不允许尝试 `CLI`。
- 任务开始时，Agent 必须向用户说明当前采用的是 `MCP`，并先完成 `MCP` preflight。
- 任务开始时，Agent 必须向用户说明当前采用的是 `workflow_stage` 串行 specialist 流，而不是 live team handoff。
- 当前平台只消费已经准备好的共享文档、workspace 与 artifact contract；若 `MCP` server 未配置完成，必须直接阻断。
- 当前宿主的 `sub_agent_mode = instruction_only_sub_agents`；支持 sub agent runtime，但如果需要 agent，只能在实例化时注入 instruction。
- 当前宿主不支持独立 agent 描述文件、native hooks 与 per-agent model control，但当前模板仍提供 wrapper skills 来统一入口语义。
- 当前模板默认不预注册 `MCP`；启用时必须按平台接线说明显式填写 opt-in MCP 配置。
- 当前平台的 `local_support` / `remote_support` / `enforcement_layer` 以 `common/config/platform_capabilities.json` 中 `manus` 行为准。

使用方式：

1. 将仓库根目录 `debugger/common/` 整体拷贝到当前平台根目录的 `common/`，覆盖占位内容。
2. 将 `RDC-Agent-Tools` 根目录整包拷贝到当前平台根目录的 `tools/`，覆盖占位内容。
3. 确认 `tools/` 下存在 `validation.required_paths` 列出的必需文件，并确认零安装入口 `rdx.bat` 与 bundled runtime 已随包覆盖。
4. 运行 `python common/config/validate_binding.py --strict`，确认 package-local `tools/`、zero-install runtime、snapshot、宿主入口文件与共享文档全部对齐。
5. 正式发起 debug 前，用户必须先提供至少一份 `.rdc`；可在当前对话上传，或提供宿主当前会话可访问的文件路径。accepted intake 后由 Agent 导入 `workspace/cases/<case_id>/inputs/captures/`。
6. 使用当前平台根目录下、与 `common/` 和 `tools/` 并列的 `workspace/` 作为运行区。
7. 完成覆盖后，再在对应宿主中打开当前平台根目录。
8. 平台启动后默认保持普通对话态；只有用户手动召唤 `rdc-debugger`，才进入调试框架。

约束：

- `common/` 默认只保留一个占位文件；正式共享正文仍由顶层 `debugger/common/` 提供，并由用户显式拷入。
- 覆盖完成后，平台根 `common/README.md` 会成为正式 shared common 的入口说明，不再保留占位语义。
- 未完成 `debugger/common/` 覆盖前，当前平台模板不可用。
- 未完成 `debugger/common/` 覆盖、`tools/` 覆盖或 binding 校验前，Agent 必须拒绝执行依赖平台真相的工作。
- 当前工具 snapshot 必须与 `RDC-Agent-Tools` 当前 catalog 完整对齐，并覆盖 `rd.vfs.*` 导航层、扩展 `rd.session.*`、`rd.core.*` discovery/observability，以及 bounded event-tree 读取语义；其中 `tabular/tsv` 仅作为 projection 支持。
- 当前平台属于 `no-hooks` tier；宿主按 `workflow_stage` 串行运行，不得伪装 host-side strict hooks。最终仍必须生成 `artifacts/run_compliance.yaml`，才算合规结案。
- 可以进行串行 specialist dispatch，但不得在该宿主上模拟实时 multi-agent handoff。
- 不得把独立 specialist 描述文件误写成 Manus 宿主能力；该宿主只支持 spawn-time instruction。
- 若任务需要更高阶 remote 多轮会话、多个 live owners 或 per-agent model routing，必须切回更高能力平台。
- 用户可通过 capture intake 在当前对话上传 `.rdc`，也可提供宿主当前会话可访问的文件路径；平台模板只负责把导入后的 case/run 现场写入 `workspace/`。