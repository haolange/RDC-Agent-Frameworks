# Codex Template（平台模板）

当前目录是 Codex 的 workspace-native 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

入口规则：

- 当前宿主可直接访问本地进程、文件系统与 workspace，默认采用 local-first。
- 默认入口是 daemon-backed `CLI`；当前宿主的 `CLI` 与 `MCP` 都依赖同一 daemon-owned runtime / context。
- 只有用户明确要求按 `MCP` 接入时，才切换到 `MCP`。
- 遇到 `qrenderdoc` 风格的 shader IR 调试诉求时，不要只停在 `force_full_precision` 一类高层 patch。
  - 优先使用 `rd.shader.get_disassembly(session_id=<session_id>, target="SPIR-V ASM")` 拿 raw asm。
  - 再用 `rd.shader.edit_and_replace(session_id=<session_id>, source_text|diff_text, source_target="SPIR-V ASM", source_encoding="spirvasm")` 做精确替换。
  - 观察与验证链仍使用现有 `texture` / `export` / `macro` tool；若最终 framebuffer 观察不等价 `qrenderdoc` 主视图，需单独记录为观察链问题，不要与 raw asm 编辑能力混淆。
  - raw asm bisect 结论必须建立在多点采样与稳定 revert 上；单次 patch 的“已应用”只证明 tool 链路成立，不足以证明该 patch 就是正确修复。
- 任务开始时，Agent 必须向用户说明当前采用的是 `CLI` 还是 `MCP`。
- 若用户要求 `MCP`，但宿主未配置对应 MCP server，必须直接阻断并提示配置。
- 当前模板默认不预注册 MCP；若要启用，使用 `.codex/config.mcp.opt-in.toml` 的示例片段显式接入。
- 当前平台的 `local_support` / `remote_support` / `enforcement_layer` 以 `common/config/platform_capabilities.json` 中 `codex` 行为准；README 不再单独发明第二套 remote 口径。

使用方式：

1. 将仓库根目录 `debugger/common/` 整体拷贝到当前平台根目录的 `common/`，覆盖占位内容。
2. 将 `RDC-Agent-Tools` 根目录整包拷贝到当前平台根目录的 `tools/`，覆盖占位内容。
3. 确认 `tools/` 下存在 `validation.required_paths` 列出的必需文件，并确认零安装入口 `rdx.bat` 与 bundled runtime 已随包覆盖。
4. 运行 `python common/config/validate_binding.py --strict`，确认 package-local `tools/`、zero-install runtime、snapshot、宿主入口文件与共享文档全部对齐。
5. 正式发起 debug 前，用户必须先提供至少一份 `.rdc`；可在当前对话上传，或提供宿主当前会话可访问的文件路径。accepted intake 后由 Agent 导入 `workspace/cases/<case_id>/inputs/captures/`。
6. 使用当前平台根目录下、与 `common/` 和 `tools/` 并列的 `workspace/` 作为运行区。
7. 完成覆盖后，打开当前目录作为 Codex workspace root。
8. 平台启动后默认保持普通对话态；只有用户手动召唤 `rdc-debugger`，才进入调试框架。除 `rdc-debugger` 之外，其他 specialist 默认都是 internal/debug-only。
9. `AGENTS.md`、`.agents/skills/`、`.codex/config.toml` 与 `.codex/agents/*.toml` 只允许引用当前平台根目录的 common/。

约束：

- `common/` 默认只保留一个占位文件；正式共享正文仍由顶层 `debugger/common/` 提供，并由用户显式拷入。
- 未完成 `debugger/common/` 覆盖前，当前平台模板不可用。
- 未完成 `debugger/common/` 覆盖、`tools/` 覆盖或 binding 校验前，Agent 必须拒绝执行依赖平台真相的工作。
- 当前工具 snapshot 必须与 `RDC-Agent-Tools` 当前 catalog 完整对齐，并覆盖 `rd.vfs.*` 导航层、扩展 `rd.session.*`、`rd.core.*` discovery/observability，以及 bounded event-tree 读取语义；其中 `tabular/tsv` 仅作为 projection 支持。
- 未提供可导入的 `.rdc` 时，Agent 必须以 `BLOCKED_MISSING_CAPTURE` 直接阻断，不得初始化 case/run 或继续 triage、investigation、planning。
- `workspace/` 预生成空骨架；真实运行产物在平台使用阶段按 case/run 写入。
- 当前平台的 remote 属于正式能力面，但统一服从 `single_runtime_owner`；若 user/backend 进入 remote，所有 live `rd.*` 只能由一个 runtime owner 持有。
- 如果维护者复核 Android remote-only 路径，当前平台应优先走 daemon-backed `CLI`，并使用 `tools/scripts/tool_contract_remote_smoke.py --rdc "<sample.rdc>" --transport daemon|mcp`。
- 对 Codex 平台，remote 是否 `verified` 以最新 smoke 报告与 `platform_capabilities.json` 当前行共同裁决，不再使用 “experimental remote” 口径。
- OpenAI Codex 当前原生支持 `AGENTS.md` 分层与 `.codex/agents/*.toml` custom agents；当前模板继续使用这两类 native surface。
- OpenAI Codex Hooks 当前只提供有限 guardrail，不足以为本框架的 native `rd.*` / specialist dispatch 提供可靠 host-side enforcement；因此当前 workspace-native 路径不引入 `.codex/hooks.json`，并按 `pseudo-hooks` 平台处理，而不是 hooks-based 平台。
- 当前平台的 enforcement 机制固定为 `runtime_owner + shared harness guard + audit artifacts`；`.codex/runtime_guard.py` 只是薄包装，唯一权威实现位于 `common/hooks/utils/harness_guard.py`。
- Codex 的执行门禁固定为：
  1. `.codex/runtime_guard.py preflight`
  2. `intent_gate`
  3. `.codex/runtime_guard.py accept-intake`：内部顺序执行 `entry-gate -> capture import -> case/run bootstrap -> intake-gate -> runtime-topology`
  4. `.codex/runtime_guard.py dispatch-readiness` / `.codex/runtime_guard.py dispatch-specialist` / `.codex/runtime_guard.py specialist-feedback`
  5. `staged_handoff`
  6. `.codex/runtime_guard.py final-audit` → `artifacts/run_compliance.yaml` pass
  7. `.codex/runtime_guard.py render-user-verdict`
- 在 `artifacts/intake_gate.yaml` 通过前，不得进入 specialist dispatch 或 live `rd.*` 分析。

Sub-Agent 工作模型：

Codex sub-agent 现已正式可用。本平台采用 `staged_handoff` coordination mode，对应以下工作模型：

- `rdc-debugger` 是 public main skill；Codex 通过 `artifacts/entry_gate.yaml + runtime_owner + run_compliance` 三层约束落地，无需 native hooks。
- 当前平台的 `sub_agent_mode = puppet_sub_agents`；Codex 有多个 sub-agent，但它们不是 `team_agents`。
- `rdc-debugger` 在 accepted intake 后必须先写出 `inputs/captures/manifest.yaml`、`capture_refs.yaml`、`notes/hypothesis_board.yaml`、`artifacts/intake_gate.yaml` 与 `artifacts/runtime_topology.yaml`，然后才允许 `staged_handoff`。
- **Sub-agents 之间不具备直接通信能力**，所有依赖、冲突与下一轮 brief 都经 `rdc-debugger` 中转。
- `staged_handoff` 在当前平台上是 hub-and-spoke 多轮接力，不是单 agent 串行切换。
- 在 local `staged_handoff` 下允许 `multi_context_orchestrated`：多个 specialist 可各持独立 context，但不能绕过 `rdc-debugger` 做 peer coordination。
- 当前平台固定声明 `specialist_dispatch_requirement = required`、`host_delegation_policy = platform_managed`、`host_delegation_fallback = none`。
- 默认 `orchestration_mode = multi_agent`；只有用户显式要求不要 multi-agent context 时，才允许 `single_agent_by_user`。
- `single_agent_by_user` 必须显式写入 `entry_gate.yaml` 与 `runtime_topology.yaml`，并由主 agent 先向用户说明当前不分派 specialist。
- specialist dispatch 后，主 agent 必须先进入 `waiting_for_specialist_brief` 视图并持续汇总阶段回报；短时 silence 不得触发 orchestrator 抢活。
- 超过框架预算仍未收到阶段回报时，应进入 `BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT` 或等价阻断状态，而不是 fallback 自执行。
- direct RenderDoc Python fallback 只允许 local backend；若走直连路径，必须记录 `fallback_execution_mode=local_renderdoc_python` 与 `WRAPPER_DEGRADED_LOCAL_DIRECT`。
- 标准分派顺序：`rdc-debugger` → `triage_agent` → `capture_repro_agent` → specialists（`pass_graph_pipeline`、`pixel_forensics`、`shader_ir`、`driver_device`）→ `skeptic_agent` → `curator_agent`。
- 每个 specialist 将结果写入 `workspace/cases/<case_id>/runs/<run_id>/notes/**` 或 `capture_refs.yaml` 后返回，`rdc-debugger` 读取后继续分派。
- Specialist 不得直接分派其他 specialist。
- `curator_agent` 在 `multi_agent` 下仍是 finalization-required；`single_agent_by_user` 下由 `rdc-debugger` 自行输出最终报告，但必须显式记录该模式。
