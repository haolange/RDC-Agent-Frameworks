# RenderDoc/RDC GPU Debug Agent Core（框架核心约束）

本文件是 `RenderDoc/RDC GPU Debug` framework 的全局约束入口。

职责边界：

- `RDC-Agent Tools` 负责平台真相：tool catalog、共享响应契约、runtime 生命周期、context/session/remote/event 语义与错误面。
- 本文件只负责 framework 如何消费这些平台真相，不重新定义平台语义。
- 角色职责正文以 `common/agents/*.md` 为准；平台适配物只允许改宿主入口、frontmatter 与少量宿主接入说明。

## 1. Framework 与 Tools 的边界

以下内容必须回到已解析的 `RDC-Agent Tools` 判定：

- `rd.*` tools 的能力面与参数语义
- 共享响应契约
- `.rdc -> capture_file_id -> session_id -> frame/event context` 的最小状态链路
- `remote_id`、`capture_file_id`、`session_id`、`active_event_id` 等 handle 的生命周期
- `context`、daemon、artifact、context snapshot 的平台语义
- preview observer 的平台语义，以及 `rd.session.get_context.preview` 作为唯一公开状态源的口径
- `spec/runtime_mode_truth.json` 对应的 transport/runtime 模式真相
- 错误分类与恢复面

以下内容属于 framework：

- 角色拓扑与协作关系
- intake、规范化、分派、阶段推进与结案门槛
- `case_input.yaml`、`reference_contract`、`fix_verification.yaml` 的合同
- `causal_anchor`、workspace、artifact/gate 的硬约束
- 多平台能力差异下的 orchestration / progress 合同

新的 orchestration SSOT 只允许落在以下 artifact/配置中：

- `common/config/platform_capabilities.json`
  - `specialist_dispatch_requirement`
  - `host_delegation_policy`
  - `host_delegation_fallback`
- `../workspace/cases/<case_id>/artifacts/entry_gate.yaml`
  - `orchestration_mode`
  - `single_agent_reason`
- `artifacts/runtime_topology.yaml`
  - `orchestration_mode`
  - `single_agent_reason`
  - `delegation_status`
  - `fallback_execution_mode`
  - `degraded_reasons`
- `runs/<run_id>/notes/hypothesis_board.yaml`
  - `active_owner`
  - `blocking_issues`
  - `progress_summary`
  - `next_actions`

## 2. Mandatory Intent Gate

所有进入 `debugger` 的正式请求，在做 debugger-specific preflight、capture intake、case/run 初始化与 specialist 分派之前，必须先由 `rdc-debugger` 执行 `intent_gate`。

硬规则：

- `rdc-debugger` 是唯一 framework classifier。
- `triage_agent`、`capture_repro_agent` 与其他 specialist 不得重做 framework 判定。
- `intent_gate` 只能由主入口 LLM 按显式 rubric 执行；不得引入 Python classifier、hook classifier 或 specialist 二次改判。
- A/B 可能只是 debugger 的证据方法，不自动等于 analyst。
- 若任务主要在问“哪里不同”，且没有 root-cause / fix-verification 目标，则必须 reject + redirect 到 `rdc-analyst`。
- 若任务主要在问性能、预算、瓶颈、收益，则必须 reject + redirect 到 `rdc-optimizer`。
- ambiguity 允许多轮澄清，且多轮期间不创建 case/run，也不创建 `hypothesis_board.yaml`。

只有当 `intent_gate.decision=debugger` 时，后续 debugger-specific preflight、capture、handoff 才允许继续。

## 3. Mandatory Entry Gate

`intent_gate` 通过后，不是直接创建 run，而是先执行 case 级 `entry_gate`。

硬规则：

- `entry_gate` 固定落盘到 `../workspace/cases/<case_id>/artifacts/entry_gate.yaml`
- 它负责裁决当前平台的 `entry_mode`、`backend`、capture 是否已提供、MCP 是否已配置，以及 remote 前置是否满足
- `entry_gate` 未通过时，不得进入 accepted intake，不得创建 `run_id`，也不得进入 live `rd.*`
- `entry_gate` 的唯一阻断码为：
  - `BLOCKED_MISSING_CAPTURE`
  - `BLOCKED_ENTRY_PREFLIGHT`
  - `BLOCKED_PLATFORM_MODE_UNSUPPORTED`
  - `BLOCKED_REMOTE_PREREQUISITE`
- framework 关于 local/remote 的正式支持级别，只能以 `common/config/platform_capabilities.json` 与 `common/config/runtime_mode_truth.snapshot.json` 为准

## 3.1 Formal Workflow State Machine

主流程固定为：

1. `preflight_pending`
2. `intent_gate_passed`
3. `entry_gate_passed`
4. `accepted_intake_initialized`
5. `intake_gate_passed`
6. `waiting_for_specialist_brief`
7. `specialist_briefs_collected`
8. `expert_investigation_complete`
9. `fix_verification_complete`
10. `skeptic_ready`
11. `curator_ready`
12. `finalized`

硬规则：

- 阶段切换必须可审计地写入 `action_chain.jsonl`
- 无 `fix_verification.yaml` 不进 skeptic
- 无 skeptic 严格 signoff 不进 curator
- 无 curator 最终写入不算 finalized
- remote blocker 和 truthful-fail verdict 必须在 patch/debug 前落盘

## 3.2 Main-Agent Overreach Is A Process Deviation

当 `coordination_mode=staged_handoff` 且 workflow 处于 `waiting_for_specialist_brief` 时，主 agent 只允许：

- 读取 brief
- 更新 `hypothesis_board.yaml`
- 做 timeout / redispatch 决策

主 agent 禁止：

- 继续 live 探索
- 替 specialist 补调查
- 抢写 specialist 证据

违反时必须在 `action_chain.jsonl` 中记为：

- `event_type: process_deviation`
- `blocking_code: PROCESS_DEVIATION_MAIN_AGENT_OVERREACH`

## 4. Mandatory Setup Verification

所有需要平台真相的工作在开始前，必须先验证以下两项均已就绪：

**检查 1：`common/` 已正确覆盖**

- 验证 `common/AGENT_CORE.md` 是否存在。
- 不存在则说明 `common/` 仍为占位目录，尚未从 `debugger/common/` 整包覆盖。

**检查 2：`tools/` 已正确覆盖**

- 验证 `tools/spec/tool_catalog.json` 是否存在。
- 不存在则说明 `tools/` 仍为占位目录，尚未从 RDC-Agent-Tools 整包覆盖。
- `tools/` 下应至少包含：
  - `README.md`
  - `docs/tools.md`
  - `docs/session-model.md`
  - `docs/agent-model.md`
  - `spec/tool_catalog.json`

强制规则：

1. 任一检查失败，必须立即停止，不得继续做 debug / investigation / tool planning。
2. 停止时统一输出：

```text
前置环境未就绪：请确认 (1) 已将 debugger/common/ 整包覆盖到平台根 common/；(2) 已将 RDC-Agent-Tools 整包覆盖到平台根 tools/；(3) 在平台根目录运行 python common/config/validate_binding.py --strict 通过后，再重新发起任务。
```

3. 不允许把 `CLI` wrapper、skill 文本、平台模板说明或模型记忆当成 Tools 真相替代品。
4. 不允许尝试搜索替代工具路径、降级处理或用其他方式绕过本检查。

## 5. Mandatory Capture Intake

所有进入 `RenderDoc/RDC GPU Debug` workflow 的任务，在开始前必须先取得至少一份用户提供的、可导入的 `.rdc`。

强制规则：

1. `.rdc` 是第一性调试输入，不是可选附件。
2. 用户可以通过两种正式方式提供 `.rdc`：在当前对话上传，或提供宿主当前会话可访问的文件路径。
3. 未提供可导入的 `.rdc` 时，必须立即停止，不得继续做 debug / investigation / tool planning / specialist dispatch / root-cause 判断。
4. capture 缺失时的统一阻断状态为：`BLOCKED_MISSING_CAPTURE`。
5. 阻断期间允许的唯一动作是提示用户上传 `.rdc`，或提供宿主当前会话可访问的文件路径。
6. 不允许用截图、日志、文本描述、skill 文本、平台模板说明或模型记忆替代 `.rdc` 作为第一性调试输入。
7. 新导入 `.rdc` 一律按 append intake 处理；不得隐式 overwrite 已有 capture。
8. `rdc-debugger` 先通过 `entry_gate`，再把 `.rdc` 导入 `inputs/captures/`，然后才允许 accepted intake 与 `run_id` 初始化。
9. 在 capture intake 完成前，不允许初始化 `run_id`、`workspace_run_root`、`case_input.yaml` 或 `runtime_topology.yaml`。

停止时统一输出：

```text
当前任务缺少必需的 capture 输入：本框架只接受基于 RenderDoc `.rdc` 的第一性调试。请先提供一份或多份 `.rdc` 文件：可以在当前对话上传，或提供宿主当前会话可访问的文件路径；收到并导入 capture 前，Agent 不会继续进行 debug、调查分派或根因判断。
```

## 6. Mandatory Intake Normalization

用户可以用自由语言描述问题，但 framework 只承认七段式 intake 被规范化后的 `case_input.yaml`。

固定模型：

- 用户层
  - `§ SESSION`
  - `§ SYMPTOM`
  - `§ CAPTURES`
  - `§ ENVIRONMENT`
  - `§ REFERENCE`
  - `§ HINTS`
  - `§ PROJECT`
- 系统层
  - `../workspace/cases/<case_id>/case_input.yaml`

硬规则：

- `rdc-debugger` 是 public main skill，负责 preflight、补料、intake 规范化、case/run 初始化与 orchestration
- specialist 不得绕过 `case_input.yaml` 直接消费原始 prose prompt 作为系统真相
- `case_input.yaml` 必须包含：
  - `session`
  - `symptom`
  - `captures`
  - `environment`
  - `reference_contract`
  - `hints`
  - `project`
- `§ CAPTURES` 只描述 replayable `.rdc`
- `§ REFERENCE` 只描述语义验收合同，不等同于某个 capture
- `visual_comparison` 只能作为 fallback/report-only 模式，不得单独支撑 `fix_verified=true`

模式约束：

- `single`
  - 必须有 `role=anomalous` capture
  - 必须有 `reference_contract`
  - 若无量化 probe 或 baseline capture，则只能 `fallback_only`
- `cross_device`
  - 必须有 `anomalous + baseline`
  - `reference_contract.source_kind` 必须为 `capture_baseline`
  - `reference_contract.source_refs` 必须包含 `capture:baseline`
- `regression`
  - 必须有 `anomalous + baseline`
  - `baseline.source` 必须为 `historical_good`
  - `baseline.provenance` 必须包含 known-good build 或 revision

## 6. Global Entry Contract

内部 `agent_id` SSOT：

- `triage_agent`
- `capture_repro_agent`
- `pass_graph_pipeline_agent`
- `pixel_forensics_agent`
- `shader_ir_agent`
- `driver_device_agent`
- `skeptic_agent`
- `curator_agent`

入口规则：

- `rdc-debugger` 是当前 framework 唯一 public main skill。
- `rdc-debugger` 也是当前 framework 唯一 classifier。
- 其他角色默认是 internal/debug-only specialist，不是正常用户入口。
- 平台启动后默认保持普通对话态；只有用户手动召唤 `rdc-debugger`，才进入 debugger workflow。
- specialist 不得绕过 `rdc-debugger` 重新定义任务 intake、验证等级、裁决门槛或 delegation policy。

## 7. Global Workflow

统一工作流：

1. `rdc-debugger`
   - 检查 `.rdc` intake
   - 规范化七段式用户输入为 `case_input.yaml`
   - 导入 capture 并写入 `inputs/captures/manifest.yaml`
   - 初始化 `run.yaml`、`capture_refs.yaml` 与 `hypothesis_board.yaml`
   - 运行 `runs/<run_id>/artifacts/intake_gate.yaml`
   - 建立 hypothesis board
   - 决定阶段推进与 specialist 分派
2. `triage_agent`
   - 结构化 symptoms / triggers
   - 推荐 SOP 与 `causal_axis`
3. `capture_repro_agent`
   - 归一化 `anomalous | baseline | fixed` capture 角色
   - 建立 capture/session 基线
   - 产出可重建的 capture anchor / runtime baton 起点
4. 因果回锚阶段
   - 将 capture/session anchor 收敛为 `causal_anchor`
   - 优先建立 `first_bad_event`、`first_divergence_event`、`root_drawcall` 或 `root_expression`
5. 专家调查阶段
   - `pass_graph_pipeline_agent`
   - `pixel_forensics_agent`
   - `shader_ir_agent`
   - `driver_device_agent`
6. 修复验证阶段
   - 产出 `runs/<run_id>/artifacts/fix_verification.yaml`
   - 明确区分 `structural_verification` 与 `semantic_verification`
7. `skeptic_agent`
   - 对 `VALIDATE -> VALIDATED` 结论做对抗审查
   - 结构通过但语义只到 fallback 时，不得严格签署
8. `curator_agent`
   - 写入 BugFull / BugCard / session artifacts

协作真相：

- `concurrent_team` 允许并行分派，但每条 live 调试链路必须独占一个 `context/daemon`
- `staged_handoff` 不是单 agent 串行；它是主 agent 为通信与裁决中枢的多 specialist 多轮接力
- `staged_handoff` 下由 specialist 先提交 brief / evidence request，再由主 agent 重组后分派到对应 context；live tool 链在 local 可由多个 specialist 各持独立 context 执行，但不得绕过主 agent 做 peer coordination
- 对 `staged_handoff` 平台，`dispatch` 与任何 live `tool_execution` 都必须晚于 `intake_gate` pass；specialist 必须把 handoff 结果写回 `runs/<run_id>/notes/**` 或 `capture_refs.yaml`
- `workflow_stage` 只允许阶段化串行推进；specialist 可按 instruction-only 方式串行实例化，但不模拟真实的 team-agent 并发 handoff
- `single_runtime_owner` 不等于 `single_agent_flow`
- remote case 一律服从 `single_runtime_owner`；可以 multi-agent coordination，但不得共享 live remote runtime
- 默认 `orchestration_mode = multi_agent`；所有平台都应先走 specialist dispatch
- 只有用户显式要求不要 multi-agent context 时，才允许 `orchestration_mode = single_agent_by_user`，并且必须把 `single_agent_reason = user_requested` 落盘到 `entry_gate.yaml` 与 `runtime_topology.yaml`
- specialist dispatch 后，主 agent 必须进入等待 brief / 汇总 progress 的编排态，不得因短时 silence 自行抢活
- 超过框架等待预算仍未收到阶段回报时，必须进入 `BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT` 或等价阻断状态，而不是 fallback 为 orchestrator 自执行
- direct RenderDoc Python fallback 只允许 local backend；若发生，必须记录 `fallback_execution_mode=local_renderdoc_python` 与 `WRAPPER_DEGRADED_LOCAL_DIRECT`

## 8. Hard Contracts

### 8.1 Causal Anchor

在做任何根因级裁决前，必须先建立 `causal_anchor`。

硬规则：

- `第一可见错误 != 第一引入错误`
- 无 `causal_anchor` 不得把 hypothesis 提升为 `VALIDATE` 或 `VALIDATED`
- screenshot / texture / similarity / screen-like fallback 只能用于选点、选对象、sanity check，不得替代因果裁决
- 结构化 `rd.*` 证据优先级高于视觉叙事
- 证据冲突时必须进入 `BLOCKED_REANCHOR`

### 8.2 Reference Contract

`reference_contract` 是语义修复验证的唯一合同。

最小字段：

- `source_kind`
- `source_refs`
- `verification_mode`
- `probe_set`
- `acceptance`

硬规则：

- `reference_contract` 不是自由文本备注；必须是结构化对象
- `source_refs` 只允许指向 `capture:<role>` 或 `reference:<id>`
- `probe_set` 缺失时，只允许 fallback 级语义验证
- `visual_comparison` 不得单独产生 strict semantic pass

### 8.3 Session / Runtime Coordination

- `session_id` 必须来自 replay session 打开链路
- 进入根因分析前必须先建立 `causal_anchor`
- `capture_file_id`、`session_id`、`active_event_id`、`remote_id` 都是短生命周期 handle
- preview 只允许作为人类同步观察面；不得把 `rd.session.get_context.preview` 当成 runtime truth、gate 输入或 fix verification 证据
- `CLI` 与 `MCP` 共用同一套 daemon / context 机制
- 同一 `context` 不得并行维护多条 live 调试链路
- 同一 `context` 可以保留多条本地 session 记录，但这只表示持久化 / 恢复能力，不表示允许多个 owner 并发共享 live runtime
- remote `open_replay` 成功后会消费 live `remote_id`
- 跨 agent 或跨轮次移交 live 调试上下文时，必须提供可重建的 `runtime_baton`
- `runtime_baton` 的恢复顺序与语义以 `common/docs/runtime-coordination-model.md` 为准

### 8.4 Workspace Contract

- `common/` 是唯一共享真相
- `../workspace/` 是 case/run 运行区

固定模型：

```text
../workspace/cases/<case_id>/
  case.yaml
  artifacts/
    entry_gate.yaml
  case_input.yaml
  inputs/
    captures/
      manifest.yaml
      <capture_id>.rdc
    references/
      manifest.yaml
      <reference_id>.png|.jpg|.md|.txt
  runs/
    <run_id>/
      run.yaml
      capture_refs.yaml
      artifacts/
        intake_gate.yaml
        runtime_topology.yaml
        runtime_batons/
        fix_verification.yaml
      logs/
      notes/
      screenshots/
      reports/
```

硬规则：

- `case` 持有原始输入池；run 只持有引用、运行现场和派生产物
- `case_input.yaml` 只允许存在于 `case` 根
- `inputs/captures/` 与 `inputs/references/` 分层，不得混放
- `inputs/captures/manifest.yaml` 是 capture 导入 provenance 的唯一 SSOT；至少记录 `capture_id`、`file_name`、`capture_role`、`source`、`import_mode`、`imported_at`、`sha256`，以及 `import_mode=path` 时的 `source_path`
- `case_input.yaml.captures[].provenance` 只描述调试语义上下文，不镜像导入路径、hash 或导入时间
- `inputs/captures/` 保存的是导入后的原始 `.rdc`；用户不负责手工把文件预放到 case 目录
- `runs/<run_id>/capture_refs.yaml` 必须显式记录 `capture_role` 与 provenance
- `artifacts/entry_gate.yaml` 是 case 级平台/模式/preflight 的唯一权威 gate artifact；未通过前不得进入 accepted intake
- `runs/<run_id>/artifacts/intake_gate.yaml` 是 run 级 intake 完整性的唯一权威 gate artifact；未通过前不得进入 specialist dispatch 或 live `rd.*`
- `runs/<run_id>/artifacts/runtime_topology.yaml` 是 run 级 context/owner/backend/entry_mode 拓扑的唯一权威 artifact
- `runs/<run_id>/artifacts/runtime_batons/` 是唯一合法的 live handoff baton 存放位置
- `runs/<run_id>/artifacts/fix_verification.yaml` 是 run 级修复验证唯一权威 artifact
- `runs/<run_id>/notes/hypothesis_board.yaml` 是 run 创建后唯一 panel/progress 结构化状态源
- `runs/<run_id>/notes/hypothesis_board.yaml` 必须包含由 `rdc-debugger` 提交的 `intent_gate` 摘要
- 第一层真相产物继续写入 `common/knowledge/library/**`
- 第二层交付层写入 `../workspace/cases/<case_id>/runs/<run_id>/reports/`

角色写入边界（write scopes）：

- `workspace_control`
  - `case.yaml`
  - `artifacts/entry_gate.yaml`
  - `case_input.yaml`
  - capture/reference manifests
  - `run.yaml`
  - `capture_refs.yaml`
  - `notes/hypothesis_board.yaml`
- `workspace_notes`
  - `runs/<run_id>/artifacts/`
  - `runs/<run_id>/notes/`
  - `runs/<run_id>/screenshots/`
- `session_signoff`
  - `common/knowledge/library/sessions/<session_id>/skeptic_signoff.yaml`
- `workspace_reports`
  - `reports/report.md`
  - `reports/visual_report.html`
- `session_artifacts`
  - `.current_session`
  - `session_evidence.yaml`
  - `action_chain.jsonl`
- `knowledge_library`
  - `bugcards/`
  - `bugfull/`
  - `bugcard_index.yaml`
  - `cross_device_fingerprint_graph.yaml`
  - `proposals/`

角色分工约束：

- `rdc-debugger` 只允许写 `workspace_control` 范围，不直接执行 live `rd.*`，也不写最终报告或知识对象
- `triage_agent`、`capture_repro_agent`、`pass_graph_pipeline_agent`、`pixel_forensics_agent`、`shader_ir_agent`、`driver_device_agent` 只允许写 `workspace_notes` 范围，并必须通过 `artifact_write` 把 handoff 结果落到 `runs/<run_id>/notes/**` 或 `capture_refs.yaml`
- `skeptic_agent` 只允许写 `session_signoff`
- `curator_agent` 负责 `workspace_reports`、`session_artifacts` 与 `knowledge_library`
- `rdc-debugger` 只在 `single_agent_by_user` 下承担调查与最终报告写入；该模式必须显式记录为用户选择，不得伪装成 native specialist / curator dispatch

### 8.5 Artifact / Gate Contract

结案前必须具备：

- `common/knowledge/library/sessions/.current_session`
- `common/knowledge/library/sessions/<session_id>/session_evidence.yaml`
- `common/knowledge/library/sessions/<session_id>/skeptic_signoff.yaml`
- `common/knowledge/library/sessions/<session_id>/action_chain.jsonl`
- `../workspace/cases/<case_id>/artifacts/entry_gate.yaml`
- `../workspace/cases/<case_id>/case_input.yaml`
- `../workspace/cases/<case_id>/inputs/captures/manifest.yaml`
- `../workspace/cases/<case_id>/inputs/references/manifest.yaml`
- `../workspace/cases/<case_id>/runs/<run_id>/capture_refs.yaml`
- `../workspace/cases/<case_id>/runs/<run_id>/artifacts/runtime_topology.yaml`
- `../workspace/cases/<case_id>/runs/<run_id>/artifacts/run_compliance.yaml`
- `../workspace/cases/<case_id>/runs/<run_id>/reports/report.md`
- `../workspace/cases/<case_id>/runs/<run_id>/reports/visual_report.html`

结案约束：

- `multi_agent` 下，`curator_agent` 仍是 finalization-required
- `single_agent_by_user` 下，允许 `rdc-debugger` 输出最终报告，但 action chain 与 runtime topology 必须显式体现该模式
- `../workspace/cases/<case_id>/runs/<run_id>/artifacts/intake_gate.yaml`
- `../workspace/cases/<case_id>/runs/<run_id>/artifacts/runtime_topology.yaml`
- `../workspace/cases/<case_id>/runs/<run_id>/artifacts/fix_verification.yaml`

额外规则：

- `entry_gate.yaml.status` 必须为 `passed`
- `session_evidence.yaml` 根对象必须包含完整 `causal_anchor`
- `session_evidence.yaml` 必须包含 `reference_contract` 摘要与 `fix_verification` 摘要
- `runtime_topology.yaml` 必须显式记录 `entry_mode`、`backend`、`orchestration_mode`、`single_agent_reason`、`sub_agent_mode`、`peer_communication`、`dispatch_topology`、`runtime_parallelism_ceiling`、`applied_live_runtime_policy`、`context_bindings`、`owners`
- `action_chain` 中所有 `dispatch`、`tool_execution`、`artifact_write`、`quality_check` 都必须携带 `entry_mode`、`backend`、`context_id`、`runtime_owner`、`baton_ref`
- `fix_verification.yaml` 必须同时包含：
  - `structural_verification`
  - `semantic_verification`
  - `overall_result`
- `overall_result` 只能由 `structural=passed && semantic=passed` 派生
- `semantic_verification.status=fallback_only` 时，严格结案无效
- preview 不进入 `entry_gate.yaml`、`intake_gate.yaml`、`runtime_topology.yaml`、`fix_verification.yaml`、`session_evidence.yaml` 的主裁决字段；如报告里提及，只能是 narrative observation

## 9. Canonical References

共享 framework 入口：

- `common/config/platform_adapter.json`
- `common/config/platform_capabilities.json`
- `common/config/platform_targets.json`
- `common/config/model_routing.json`

共享 framework 文档：

- `common/docs/intake/README.md`
- `common/docs/cli-mode-reference.md`
- `common/docs/model-routing.md`
- `common/docs/platform-capability-matrix.md`
- `common/docs/platform-capability-model.md`
- `common/docs/runtime-coordination-model.md`
- `common/docs/truth_store_contract.md`
- `common/docs/workspace-layout.md`
- `common/docs/action_chain_schema.yaml`
- `common/docs/counterfactual_scoring_spec.md`

角色与技能入口：

- `common/agents/*.md`
- `common/skills/rdc-debugger/SKILL.md`
- `common/skills/*/SKILL.md`

