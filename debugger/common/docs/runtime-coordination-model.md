# 运行协调模型

本文定义 framework 如何消费 Tools 的 runtime truth，并把它落成可执行、可审计、可终局检查的协作协议。

## 1. 四层概念

- `entry_mode`
  - `cli` 或 `mcp`
- `backend`
  - `local` 或 `remote`
- `coordination_mode`
  - `concurrent_team`、`staged_handoff`、`workflow_stage`
- `orchestration_mode`
  - `multi_agent` 或 `single_agent_by_user`

它们不是同一维度，不允许互相代替。

## 2. Workflow State Machine

主流程固定为以下可审计状态：

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

- 阶段允许受控回转，但只能回到框架文档显式列出的状态。
- 每次阶段切换都必须在 `action_chain.jsonl` 中记录 `workflow_stage_transition`。
- 每次回转都必须记录触发来源、证据缺口与下一步动作。
- `fix_verification_complete` 之前不得进入 skeptic。
- 没有 skeptic 严格 signoff 不得进入 curator。
- 没有 curator 的最终写入，不得视为 `finalized`。

## 3. Clarification / Redispatch Model

闭环回转只允许以下入口：

- triage 置信度不足
  - 进入 `triage_needs_clarification`
- 缺失关键输入
  - 进入 `requesting_additional_input`
- specialist brief 证据链不闭合
  - 进入 `redispatch_pending`
- redispatch 后继续调查
  - 进入 `specialist_reinvestigation`
- skeptic 发起 challenge
  - 进入 `skeptic_challenged`
- specialist 超时
  - 进入 `blocked_specialist_timeout`

硬规则：

- triage 不直接调度 specialist，只输出 `route_confidence`、`clarification_needed`、`missing_inputs_for_routing`。
- orchestrator 才能决定是否补料、回退或重新分派。
- 回转不是静默重试。每次 redispatch 都必须更新 `runtime_topology.yaml` 与 `hypothesis_board.yaml`。
- 连续失败超过预算时，必须回退到 orchestrator 重新请求 capture / reference，或输出 blocker。

## 4. Remote Gate Model

remote 子状态与 gate 固定为：

- `remote_prerequisite_gate`
- `remote_capability_gate`
- `remote_reconnect_required`
- `remote_fix_verification_blocked_by_capability`

硬规则：

- remote blocker 必须在 patch/debug 前落盘。
- remote truthful-fail verdict 必须基于 Tools 的 `remote_capability_matrix`，不能靠框架猜测。
- `runtime_mode_truth.snapshot.json` 只表达 runtime ceiling；remote 细粒度能力必须来自 `rd.session.get_context` 或 `rd.core.get_capabilities`。

## 5. Context And Ownership

- `context` 是 live runtime 隔离单元，不是多 agent 共享黑箱。
- 并行 case 也必须拆成独立 `context/daemon`。
- `remote_context_locality=strict` 与 `remote_handle_reuse_policy=must_reconnect` 是硬约束。
- remote live runtime 一律是 `single_runtime_owner`。
- local 可按平台矩阵消费成：
  - `multi_context_multi_owner`
  - `multi_context_orchestrated`
  - `single_runtime_owner`

## 6. Staged Handoff Contract

`staged_handoff` 不是单 agent 串行切换，而是主 agent 作为通信与裁决中枢的多 specialist 多轮接力。

主 agent 在 `waiting_for_specialist_brief`、`redispatch_pending`、`specialist_reinvestigation`、`skeptic_challenged` 期间只允许：

- 读取 specialist brief 或 skeptic challenge
- 更新 `notes/hypothesis_board.yaml`
- 记录 blocker / challenge / timeout
- 做 timeout / redispatch / request-more-input 决策

主 agent 在这些阶段禁止：

- 自己继续 live 探索
- 代替 specialist 补调查
- 抢写 specialist notes
- 抢跑 patch/debug

若违反，必须在 `action_chain.jsonl` 记为：

- `process_deviation`
- `blocking_code: PROCESS_DEVIATION_MAIN_AGENT_OVERREACH`

## 7. Timeout Model

- specialist 首次 brief 超过预算未返回时，必须记录 timeout blocker
- 持续执行中长时间无阶段更新时，必须进入 `blocked_specialist_timeout`
- timeout 之后允许的动作只有：阻断、请求补料、重新分派、终止当前路径并回退到 orchestrator

硬规则：

- timeout 不得自动退化为 orchestrator 自执行
- timeout 事件必须写入 `action_chain.jsonl`
- `runtime_topology.yaml.last_timeout_at` 必须同步更新

## 8. Orchestration Modes

### `multi_agent`

- 默认模式
- 必须走 specialist dispatch
- `rdc-debugger` 负责 orchestration、gate、阶段推进、补料、redispatch 和 final gate

### `single_agent_by_user`

- 只有用户显式要求不要 multi-agent context 时才允许进入
- 必须同时落盘到 `entry_gate.yaml` 与 `runtime_topology.yaml`
- 必须显式记录：
  - `orchestration_mode: single_agent_by_user`
  - `single_agent_reason: user_requested`
  - `delegation_status: single_agent_by_user`

## 9. Runtime Baton Contract

跨 agent、跨轮次、跨重连传递 live 调试上下文时：

- 必须使用 `runtime_baton`
- `rd.session.resume` / `rd.session.rehydrate_runtime_baton` 必须声明 `baton_ref`
- baton 只承载同一 run 内的恢复事实，不改变 remote 单 owner 规则
- baton 不得暗示跨 run session continuity

## 10. Run Lifecycle Rules

- 每个 `run` 是独立 session 审计单元
- reopen / reconnect 生成新的 `session_id` / `context_id` 是预期行为
- 跨 run 复用的是历史 evidence / reports / knowledge objects
- 历史 run 只能通过结构化 artifact 被召回，不能复用旧 live handle

## 11. Required Audit Surface

以下对象共同组成 runtime coordination audit surface：

- `entry_gate.yaml`
- `intake_gate.yaml`
- `runtime_topology.yaml`
- `fix_verification.yaml`
- `action_chain.jsonl`
- `session_evidence.yaml`
- `skeptic_signoff.yaml`
- `run_compliance.yaml`

补充约束：

- `rd.session.get_context.preview` 只属于 human observer surface。
- `rd.session.get_context.preview.display` 只属于 narrative observation。

## 12. Role Whitelist Summary

- `rdc-debugger`
  - 允许：intent gate、entry/intake gate、request-more-input、dispatch、workflow stage transition、timeout/redispatch、final gate
  - 禁止：在 specialist 等待期或 challenge 期做 specialist live investigation
- specialists
  - 允许：按各自 write scope 做调查、brief、证据落盘
  - 禁止：重判 intent gate、修改平台策略、直接 finalization
- `skeptic_agent`
  - 允许：读取 `fix_verification` 与 session truth，输出 signoff/challenge
  - 禁止：补调查、改报告、改 knowledge object
- `curator_agent`
  - 允许：在 skeptic strict signoff 后先做知识沉淀裁决，再做 final artifacts
  - 禁止：替代 skeptic 审批，或在 fix verification / fix reference readiness 缺失时 finalize
