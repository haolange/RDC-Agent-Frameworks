# RenderDoc/RDC Debugger Runtime Coordination Model

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

- 阶段只能前进，不能跳级 finalize。
- 每次阶段切换都必须在 `action_chain.jsonl` 中记录 `workflow_stage_transition`。
- `fix_verification_complete` 之前不得进入 skeptic。
- 没有 skeptic 严格 signoff 不得进入 curator。
- 没有 curator 的最终写入，不得视为 `finalized`。

## 3. Remote Gate Model

remote 子状态与 gate 固定为：

- `remote_prerequisite_gate`
- `remote_capability_gate`
- `remote_reconnect_required`
- `remote_fix_verification_blocked_by_capability`

硬规则：

- remote blocker 必须在 patch/debug 前落盘。
- remote truthful-fail verdict 必须基于 Tools 的 `remote_capability_matrix`，不能靠框架猜测。
- `runtime_mode_truth.snapshot.json` 只表达 runtime ceiling；remote 细粒度能力必须来自 `rd.session.get_context` 或 `rd.core.get_capabilities`。

## 4. Context And Ownership

- `context` 是 live runtime 隔离单元，不是多 agent 共享黑箱。
- 并行 case 也必须拆成独立 `context/daemon`。
- `remote_context_locality=strict` 与 `remote_handle_reuse_policy=must_reconnect` 是硬约束。
- remote live runtime 一律是 `single_runtime_owner`。
- local 可按平台矩阵消费成：
  - `multi_context_multi_owner`
  - `multi_context_orchestrated`
  - `single_runtime_owner`

框架只允许如下映射：

- `local + concurrent_team` -> 可消费 `multi_context_multi_owner`
- `local + staged_handoff` -> 可消费 `multi_context_orchestrated`
- `remote + any coordination_mode` -> 固定 `single_runtime_owner`
- `workflow_stage` -> 固定串行 specialist 形态，不模拟 team-agent live mesh

权威短语：

- `remote_coordination_mode = single_runtime_owner`
- `single_runtime_owner != single_agent_flow`

## 5. Staged Handoff Contract

`staged_handoff` 不是单 agent 串行切换，而是主 agent 作为通信与裁决中枢的多 specialist 多轮接力。

主 agent 在 `waiting_for_specialist_brief` 期间只允许：

- 读取 specialist brief
- 更新 `notes/hypothesis_board.yaml`
- 记录 blocker
- 做 timeout / redispatch 决策

主 agent 在该阶段禁止：

- 自己继续 live 探索
- 代替 specialist 补调查
- 抢写 specialist notes
- 抢跑 patch/debug

若违反，必须在 `action_chain.jsonl` 记为：

- `process_deviation`
- `blocking_code: PROCESS_DEVIATION_MAIN_AGENT_OVERREACH`

## 6. Orchestration Modes

### `multi_agent`

- 默认模式
- 必须走 specialist dispatch
- `rdc-debugger` 负责 orchestration、gate、阶段推进和最终裁决前置条件

### `single_agent_by_user`

- 只有用户显式要求不要 multi-agent context 时才允许进入
- 这不是 degraded path
- 必须同时落盘到：
  - `entry_gate.yaml`
  - `runtime_topology.yaml`
- 必须显式记录：
  - `orchestration_mode: single_agent_by_user`
  - `single_agent_reason: user_requested`
  - `delegation_status: single_agent_by_user`
- specialist 长时间无回报时必须进入 `BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT` 或等价阻断状态，而不是让 orchestrator 抢做 specialist live investigation

## 7. Runtime Baton Contract

跨 agent、跨轮次、跨重连传递 live 调试上下文时：

- 必须使用 `runtime_baton`
- `rd.session.resume` / `rd.session.rehydrate_runtime_baton` 必须声明 `baton_ref`
- 对 `multi_context_orchestrated`，跨 context live handoff 必须有 baton
- baton 只承载恢复事实，不改变 remote 单 owner 规则

## 8. Required Audit Surface

以下对象共同组成 runtime coordination audit surface：

- `entry_gate.yaml`
- `intake_gate.yaml`
- `runtime_topology.yaml`
- `fix_verification.yaml`
- `action_chain.jsonl`
- `session_evidence.yaml`
- `skeptic_signoff.yaml`
- `run_compliance.yaml`

remote run 额外要求：

- `remote_prerequisite_gate.yaml`
- `remote_capability_gate.yaml`
- `remote_recovery_decision.yaml`
- `notes/remote_planning_brief.yaml`
- `notes/remote_runtime_inconsistency.yaml`

补充约束：

- `rd.session.get_context.preview` 只属于 human observer surface。
- 它不进入 runtime coordination audit surface，也不改变 `runtime_topology.yaml` / gate 的主真相定义。

## 9. Role Whitelist Summary

- `rdc-debugger`
  - 允许：intent gate、entry/intake gate、dispatch、workflow stage transition、timeout/redispatch、final gate
  - 禁止：在 `waiting_for_specialist_brief` 期间做 specialist live investigation
- specialists
  - 允许：按各自 write scope 做调查、brief、证据落盘
  - 禁止：重判 intent gate、修改平台策略、直接 finalization
- `skeptic_agent`
  - 允许：读取 `fix_verification` 与 session truth，输出 signoff/challenge
  - 禁止：补调查、改报告、改 knowledge object
- `curator_agent`
  - 允许：在 skeptic strict signoff 后生成 final artifacts
  - 禁止：替代 skeptic 审批，或在 fix verification 缺失时 finalize
