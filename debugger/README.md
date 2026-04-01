# RenderDoc/RDC GPU Debug（调试框架）

`debugger/` 是 `RDC-Agent-Frameworks` 中面向 RenderDoc/RDC GPU 调试场景的专属 framework 根目录。
本 framework 依赖的 `Tools` 真相边界聚焦于“打开 `.rdc` 后做离线 replay、调试和导出”，不把任意 app 控制面视为默认公开能力。
这里定义 `debugger` 自身的运行前提、共享运行时文档入口、平台模板使用方式与维护者文档边界；仓库根 `README.md` 不承载这些规则。

当前框架已经从“严格线性 staged handoff”收敛为“强前置参照 + 受控回转 + 可审计 finalization”的闭环调试框架：

- `.rdc` 与 `fix reference` 同属正式入口前置；缺任一项都不得进入 accepted intake。
- `reference_contract` 既是修复验证合同，也是 run 初始化前必须满足的结构化参照合同。
- specialist handoff 允许有限回转，但所有澄清、challenge、timeout、redispatch 都必须落盘并进入审计面。
- reopen / reconnect 产生新的 `session_id` / `context_id` 属于预期行为；跨 run 复用的是历史 evidence，而不是 live handle。

当前 `shader` 相关能力已把 raw `SPIR-V Asm` 纳入现有 `rd.shader.*` tool 的正式扩展面：

- 推荐工作流是 `rd.shader.get_disassembly(target="SPIR-V ASM") -> rd.shader.edit_and_replace(source_text|diff_text, source_target="SPIR-V ASM", source_encoding="spirvasm") -> validate -> rd.shader.revert_replacement`。
- 这条链需要配套多点验证。raw asm 精确 patch 成功，只能证明工具链具备等价编辑和应用能力，不代表当前删掉的 `RelaxedPrecision` decoration 一定就是正确修复；样本级 bisect 仍要看多个像素点与回滚后一致性。
- 这条链解决的是精确 IR patch / apply / revert 语义，不等价于 `qrenderdoc` 主视窗的最终 framebuffer 观察链；若 UI 主视图与 `rd.export.screenshot` 不一致，应单独按 framebuffer 观察问题处理。
- 当前 `Tools` 已公开 context 绑定 preview：它只给人类同步观察 `current_session_id + active_event_id`，不进入 framework 的 gate / evidence / fix verification 主真相链。
- framework 如需向用户解释当前观察窗口，可读取 `rd.session.get_context.preview.display` 中的 `output_slot`、`framebuffer_extent`、`viewport_rect`、`scissor_rect` 与 `window_rect`；这些字段只属于 human observer surface，不提升为 structure truth。

## 使用前提

开始使用 `debugger/` 之前，必须先完成：

1. 将仓库根目录 `debugger/common/` 整体拷贝到目标平台根目录的 `common/`。
2. 将 `RDC-Agent-Tools` 根目录整包拷贝到目标平台根目录的 `tools/`。
3. 确认 `tools/` 下存在 `validation.required_paths` 列出的必需文件：`README.md`、`docs/tools.md`、`docs/session-model.md`、`docs/agent-model.md`、`spec/tool_catalog.json`、`rdx.bat`、`binaries/windows/x64/manifest.runtime.json`、`binaries/windows/x64/python/python.exe`。
4. 运行 `python common/config/validate_binding.py --strict`，确认 package-local `tools/`、zero-install runtime、snapshot 与宿主入口文件全部对齐。
5. 先提供至少一份 `.rdc`：可以在当前对话上传，也可以提供宿主当前会话可访问的文件路径。
6. 同时提供结构化 `fix reference`：至少要有可解析的 `reference_contract`，并达到 `readiness_status = strict_ready`。缺失、仅自由文本描述、或只能 `fallback_only` 的参照都不得进入 accepted intake。

补充约束：

- `platform_adapter.json` 中的 `paths.tools_source_root` 固定为 `tools`；它只表示 package-local source payload，不是 live runtime 目录或手工绑定步骤。
- source repo 中的 `tools/` 仍是平台模板占位目录；正式工具真相只来自复制后的平台包根目录 `tools/`。
- 当前 `Tools` 的正式用户入口是 `tools/rdx.bat`；若宿主按 `MCP` 接线，应通过 `cmd /c tools/rdx.bat --non-interactive mcp` 或等价包装调用，而不是把系统 `Python` 当成正式前提。
- `rd.vfs.*` 是只读导航层，用于 browse-only 结构探索；精确调试、导出与状态变更必须回到 canonical `rd.*`。
- `tabular/tsv` 只是 projection/summary 格式，用于提升扫描效率，不表示语义重要度排序。

未完成以上步骤前：

- Agent 不得进入依赖平台真相的工作。
- 尚未提供可导入的 `.rdc` 时，Agent 必须以 `BLOCKED_MISSING_CAPTURE` 阻断，不得初始化 case/run 或继续调查。
- 尚未提供通过门禁的 `fix reference` 时，Agent 必须以 `BLOCKED_MISSING_FIX_REFERENCE` 阻断，不得初始化 case/run 或继续调查。
- `README.md`、`AGENT_CORE.md`、skills 与平台模板都只能提供 framework 约束，不能替代 `Tools` 真相。

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

平台模板位于 `platforms/<platform>/`。标准用户工作流：

1. 选择目标平台模板目录。
   - `claude-code`
   - `code-buddy`
   - `codex`
   - `copilot-cli`
2. 将仓库根目录 `debugger/common/` 整体拷贝到该平台根的 `common/`。
3. 将 `RDC-Agent-Tools` 根目录整包拷贝到该平台根的 `tools/`。
4. 运行 `python common/config/validate_binding.py --strict`，确认 package-local `tools/`、zero-install runtime、snapshot 与宿主入口文件都已对齐。
5. 完成覆盖后，在对应宿主中打开该平台根目录。
6. 正常用户请求从 `rdc-debugger` 发起；`rdc-debugger` 与其他 specialist 角色默认是 internal/debug-only。
7. 发起 debug 任务时，用户必须先提供一份或多份 `.rdc`，并同时提供可执行的 `fix reference`；accepted intake 后才允许创建 case/run。

说明：

- 平台内 `common/` 与 `tools/` 默认都只保留最小占位目录，用于等待整包覆盖。
- 未同时完成 `common/` 覆盖、`tools/` 覆盖与 binding 校验前，平台模板不可用。
- 平台入口选择必须遵循 shared docs 的统一规则：可直达本地环境的宿主默认 local-first / daemon-backed `CLI`；不能直达本地环境的宿主默认 `MCP`。
- 任务开始时，Agent 必须向用户说明当前采用的入口模式；若所选入口的前置条件未满足，必须先阻断。
- `rdc-debugger` 是当前 framework 唯一 public main skill；`rdc-debugger` 只承担 orchestration + intake normalization。
- 用户不负责手工把 `.rdc` 预放进 `workspace/`；accepted intake 后由 Agent 创建 case/run，并把 `.rdc` 导入 `workspace/cases/<case_id>/inputs/captures/`。

## 当前平台入口模式

当前平台分组以 `common/config/platform_capabilities.json` 为唯一权威源：

- 默认 `CLI`，但用户可强制切到 `MCP`
  - `codex`
  - `claude-code`
  - `code-buddy`
  - `copilot-cli`

这里的 `CLI` / `MCP` 只表示工具入口模式，不改变各平台现有的 `concurrent_team`、`staged_handoff`、`workflow_stage` 协作上限。
