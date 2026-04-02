# 运行协调模型

本文定义 framework 如何消费 Tools 的 runtime truth，并把它落成 broker-owned staged handoff 协议。

本文只覆盖 `Audited Execution Phase`。`Plan / Intake Phase` 不持有 live runtime，不创建 case/run，也不产出 run 级 runtime artifacts。

## 1. 固定概念

- `entry_mode`
  - `cli` 或 `mcp`
- `backend`
  - `local` 或 `remote`
- `coordination_mode`
  - 只允许 `staged_handoff`
- `orchestration_mode`
  - 只允许 `multi_agent`
- `live_runtime_policy`
  - 只允许 `single_runtime_single_context`

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

补充说明：

- 用户第一次唤起 `rdc-debugger` 不等于进入本状态机
- 只有 `debug_plan.execution_readiness = ready` 后，才允许从 `entry_gate` 进入本状态机

## 3. Runtime Ownership Model

- broker 始终直接持有 tools process
- 同一时刻只允许一个 `ownership_lease`
- specialist 在有效 lease 下直接向 broker 提交结构化 action request
- broker 校验 owner、lease epoch、阶段合法性与 action scope
- 临时 wrapper 封装 live CLI 一律阻断

## 4. Runtime SSOT Artifacts

- `runtime_session.yaml`
  - `runtime_generation`、`process_status`、`session_id`、`context_id`、`active_owner_agent_id`、`lease_epoch`、`continuity_status`
- `runtime_snapshot.yaml`
  - `snapshot_rev`、`active_event_id`、`selected_resource`、`pipeline_stage`、`view_intent`、`last_successful_action`
- `ownership_lease.yaml`
  - `owner_agent_id`、`lease_epoch`、`issued_at`、`expires_at`、`handoff_from`、`allowed_action_classes`
- `runtime_failure.yaml`
  - `failure_class`、`recovery_attempted`、`runtime_generation_before/after`、`continuity_status`、`blocking_code`

## 5. Clarification / Redispatch Model

闭环回转只允许以下入口：

- triage 置信度不足
- 缺失关键输入
- specialist brief 证据链不闭合
- skeptic 发起 challenge
- specialist 超时

回转不是静默重试。每次 redispatch 都必须写入 `action_chain.jsonl` 并更新 `hypothesis_board.yaml`。

Plan 阶段的澄清不属于这里的 redispatch；只有进入 execution 后的补料/回转才写入审计链。

## 6. Final Gate

- 没有 `fix_verification` 不进 skeptic
- 没有 skeptic strict signoff 不进 curator
- 没有 curator 最终写入不算 `finalized`
- 有 active `ownership_lease`、blocked `runtime_failure`、未确认 continuity 时不得 finalized
