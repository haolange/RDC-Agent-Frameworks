# RenderDoc/RDC GPU Debug 框架核心约束

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
- preview observer 的平台语义，以及 `rd.session.get_context.preview` / `rd.session.get_context.preview.display` 作为唯一公开状态源的口径
- `spec/runtime_mode_truth.json` 对应的 transport/runtime 模式真相
- 错误分类与恢复面

以下内容属于 framework：

- 角色拓扑与协作关系
- intake、规范化、分派、阶段推进、回转与结案门槛
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
  - `fix_reference_status`
  - `allowed_to_initialize_run`
- `runs/<run_id>/artifacts/intake_gate.yaml`
  - `reference_readiness`
  - `clarification_required`
  - `redispatch_allowed`
- `artifacts/runtime_topology.yaml`
  - `orchestration_mode`
  - `single_agent_reason`
  - `delegation_status`
  - `fallback_execution_mode`
  - `degraded_reasons`
  - `investigation_round`
  - `redispatch_count`
  - `last_challenge_source`
  - `last_timeout_at`
- `runs/<run_id>/notes/hypothesis_board.yaml`
  - `active_owner`
  - `blocking_issues`
  - `progress_summary`
  - `next_actions`
  - `current_loop_reason`
  - `evidence_gap_summary`
  - `last_specialist_round`
  - `remaining_retry_budget`

## 2. 必须执行的意图闸门

所有进入 `debugger` 的正式请求，在做 debugger-specific preflight、capture intake、reference intake、case/run 初始化与 specialist 分派之前，必须先由 `rdc-debugger` 执行 `intent_gate`。

硬规则：

- `rdc-debugger` 是唯一 framework classifier。
- `triage_agent`、`capture_repro_agent` 与其他 specialist 不得重做 framework 判定。
- `triage_agent` 可以读取历史 BugCard / BugFull 与 active taxonomy / invariant / SOP，给主 agent 提供探索方向建议，但不得重判 intent gate、不得替代主 agent 做 orchestration。
- `intent_gate` 只能由主入口 LLM 按显式 rubric 执行；不得引入 Python classifier、hook classifier 或 specialist 二次改判。
- A/B 可能只是 debugger 的证据方法，不自动等于 analyst。
- 若任务主要在问“哪里不同”，且没有 root-cause / fix-verification 目标，则必须 reject + redirect 到 `rdc-analyst`。
- 若任务主要在问性能、预算、瓶颈、收益，则必须 reject + redirect 到 `rdc-optimizer`。
- ambiguity 允许多轮澄清，且多轮期间不创建 case/run，也不创建 `hypothesis_board.yaml`。

只有当 `intent_gate.decision=debugger` 时，后续 debugger-specific preflight、capture、reference、handoff 才允许继续。

## 3. 必须执行的入口闸门

`intent_gate` 通过后，不是直接创建 run，而是先执行 case 级 `entry_gate`。

硬规则：

- `entry_gate` 固定落盘到 `../workspace/cases/<case_id>/artifacts/entry_gate.yaml`
- 它负责裁决当前平台的 `entry_mode`、`backend`、capture 是否已提供、fix reference 是否 strict-ready、MCP 是否已配置，以及 remote 前置是否满足
- `entry_gate` 未通过时，不得进入 accepted intake，不得创建 `run_id`，也不得进入 live `rd.*`
- `entry_gate` 的唯一阻断码为：
  - `BLOCKED_MISSING_CAPTURE`
  - `BLOCKED_MISSING_FIX_REFERENCE`
  - `BLOCKED_ENTRY_PREFLIGHT`
  - `BLOCKED_PLATFORM_MODE_UNSUPPORTED`
  - `BLOCKED_REMOTE_PREREQUISITE`

### 3.1 Fix Reference 门禁

`reference_contract` 从“验证合同”提升为“run 初始化前必须满足的结构化参照合同”。

最小字段：

- `source_kind`
- `source_refs`
- `verification_mode`
- `probe_set`
- `acceptance`
- `readiness_status`

`readiness_status` 只允许：

- `strict_ready`
- `fallback_only`
- `missing`

硬规则：

- 只有 `strict_ready` 才允许通过 `entry_gate` 与 `intake_gate`
- `fallback_only` 与 `missing` 都必须阻断 accepted intake
- 自由文本“正确效果描述”不能单独算作 fix reference
- `visual_comparison` 只能属于 narrative / report 观察，不得单独把 `readiness_status` 提升为 `strict_ready`

## 4. 正式工作流状态机

主流程固定为以下可审计状态集合：

1. `preflight_pending`
2. `intent_gate_passed`
3. `awaiting_fix_reference`
4. `entry_gate_passed`
5. `accepted_intake_initialized`
6. `triage_needs_clarification`
7. `requesting_additional_input`
8. `intake_gate_passed`
9. `waiting_for_specialist_brief`
10. `redispatch_pending`
11. `specialist_reinvestigation`
12. `specialist_briefs_collected`
13. `expert_investigation_complete`
14. `skeptic_challenged`
15. `fix_verification_complete`
16. `skeptic_ready`
17. `curator_ready`
18. `finalized`
19. `blocked_specialist_timeout`

硬规则：

- 阶段切换必须可审计地写入 `action_chain.jsonl`
- 阶段允许受控回转，但只能回到文档明确列出的状态，不允许静默重跑
- 无 `fix_verification.yaml` 不进 skeptic
- 无 skeptic 严格 signoff 不进 curator
- 无 curator 最终写入不算 finalized

### 4.1 回转入口

- triage 置信度不足时，必须回到 `triage_needs_clarification` 或 `requesting_additional_input`
- orchestrator 发现关键输入缺口时，必须回到 `requesting_additional_input`
- specialist brief 证据链不闭合时，必须进入 `redispatch_pending` 或 `specialist_reinvestigation`
- skeptic challenge 未关闭时，必须进入 `skeptic_challenged`
- specialist 超时或连续无进展时，必须进入 `blocked_specialist_timeout`，并以 `BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT` 作为显式阻断码

## 5. 主 Agent 越权属于流程偏差

当 `coordination_mode=staged_handoff` 且 workflow 处于 `waiting_for_specialist_brief`、`redispatch_pending`、`specialist_reinvestigation` 或 `skeptic_challenged` 时，主 agent 只允许：

- 读取 brief / challenge
- 更新 `hypothesis_board.yaml`
- 记录 blocker
- 做 timeout / redispatch / request-more-input 决策

主 agent 禁止：

- 继续 live 探索
- 替 specialist 补调查
- 抢写 specialist 证据

违反时必须在 `action_chain.jsonl` 中记为：

- `event_type: process_deviation`
- `blocking_code: PROCESS_DEVIATION_MAIN_AGENT_OVERREACH`

## 6. 必须执行的环境验证

所有需要平台真相的工作在开始前，必须先验证以下两项均已就绪：

- `common/AGENT_CORE.md`
- `tools/spec/tool_catalog.json` 与 `tools/rdx.bat`

任一检查失败，必须立即停止，不得继续做 debug / investigation / tool planning。

## 7. 必须执行的 Capture / Reference Intake

所有进入 `RenderDoc/RDC GPU Debug` workflow 的任务，在开始前必须先取得：

- 至少一份用户提供的、可导入的 `.rdc`
- 一份结构化、可执行、`strict_ready` 的 `fix reference`

capture 来源可以是：

- 在当前对话上传 `.rdc`
- 提供当前宿主可访问的文件路径

强制规则：

- 未提供可导入的 `.rdc` 时，统一阻断码为 `BLOCKED_MISSING_CAPTURE`
- 未提供通过门禁的 `fix reference` 时，统一阻断码为 `BLOCKED_MISSING_FIX_REFERENCE`
- 在 capture/reference intake 完成前，不允许初始化 `run_id`、`workspace_run_root`、`case_input.yaml` 或 `runtime_topology.yaml`

## 8. 必须执行的 Intake 规整

用户可以用自由语言描述问题，但 framework 只承认七段式 intake 被规范化后的 `case_input.yaml`。

硬规则：

- `case_input.yaml` 必须包含 `reference_contract`
- `reference_contract.readiness_status` 必须存在，且 accepted intake 前只能为 `strict_ready`
- `visual_comparison` 不得单独产生 strict semantic pass

## 9. 全局入口契约

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

## 10. 全局工作流

统一工作流：

1. `rdc-debugger`
   - 检查 `.rdc` intake
   - 检查 `fix reference` readiness
   - 规范化七段式用户输入为 `case_input.yaml`
   - 导入 capture 并写入 `inputs/captures/manifest.yaml`
   - 初始化 `run.yaml`、`capture_refs.yaml` 与 `hypothesis_board.yaml`
   - 运行 `runs/<run_id>/artifacts/intake_gate.yaml`
   - 决定阶段推进、补料、specialist 分派与 redispatch
2. `triage_agent`
   - 输出 `route_confidence`、`clarification_needed` 与 `missing_inputs_for_routing`
3. `capture_repro_agent`
   - 建立 capture/session 基线
   - 校验 capture 是否与当前 `fix reference` 可对齐
4. specialists
   - 只做各自调查与 brief
5. `skeptic_agent`
   - 对每轮 investigation 的证据闭环做仲裁
6. `curator_agent`
   - 先做知识沉淀裁决，再做报告收尾

## 11. Session / Runtime 协调

- 每个 `run` 是独立 session 审计单元
- reopen / reconnect 生成新的 `session_id` / `context_id` 属于预期行为
- 跨 run 复用的是历史 evidence / knowledge / reports，不是 live handle
- `runtime_baton` 只服务同一 run 内的恢复与交接，不暗示跨 run session continuity

## 12. Artifact / Gate 契约

结案前必须具备：

- `entry_gate.yaml`
- `intake_gate.yaml`
- `runtime_topology.yaml`
- `fix_verification.yaml`
- `action_chain.jsonl`
- `session_evidence.yaml`
- `skeptic_signoff.yaml`
- `run_compliance.yaml`

额外规则：

- `entry_gate.yaml.fix_reference_status` 必须为 `strict_ready`
- `runtime_topology.yaml` 必须记录 `investigation_round`、`redispatch_count`、`last_challenge_source`、`last_timeout_at`
- `action_chain` 中所有 `dispatch`、`tool_execution`、`artifact_write`、`quality_check`、`challenge`、`request_more_input`、`timeout_blocker` 都必须携带 runtime 审计字段
- `semantic_verification.status=fallback_only` 时，严格结案无效

## 13. 权威参考

共享 framework 文档：

- `common/docs/intake/README.md`
- `common/docs/runtime-coordination-model.md`
- `common/docs/truth_store_contract.md`
- `common/docs/workspace-layout.md`

角色与技能入口：

- `common/agents/*.md`
- `common/skills/rdc-debugger/SKILL.md`
- `common/skills/*/SKILL.md`
