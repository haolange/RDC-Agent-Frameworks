---
name: rdc-debugger
description: Public main skill for the RenderDoc/RDC GPU debugger framework. Use when the user wants defect diagnosis, root-cause analysis, regression explanation, or fix verification from one or more `.rdc` captures. This skill owns intent gate classification, plan/intake normalization, debug_plan handoff, execution gating, broker-owned specialist dispatch, redispatch, timeout handling, and verdict gating.
---

# RDC 调试器

`rdc-debugger` 是唯一 public main skill 与唯一 classifier，但内部固定分成两段：

1. `Plan / Intake Phase`
2. `Audited Execution Phase`

## Plan / Intake Phase

Plan 阶段负责：

- `intent_gate`
- 缺失输入补料
- 生成 `reference_contract`
- 判定 `strict_ready / fallback_only / missing`
- 汇总为 `debug_plan`

Plan 阶段默认通过轻量 sub-agent 收敛输入：

- `clarification_agent`
- `reference_contract_agent`
- `plan_compiler_agent`

Plan 阶段硬规则：

- 不创建 case/run
- 不写 `action_chain.jsonl`、`session_evidence.yaml`、`skeptic_signoff.yaml`
- 不接触 live runtime
- orchestrator 只保留核心简化摘要，不回灌冗长问答全文和大段中间推理

## Audited Execution Phase

只有当 `debug_plan.execution_readiness = ready` 时，才允许进入 execution。

你必须按固定阶段链推进：

1. `entry_gate`
2. `accept_intake / intake_gate`
3. `triage`
4. `dispatch_readiness`
5. `specialist handoff / redispatch / timeout`
6. `skeptic`
7. `curator`
8. `final_audit / render_user_verdict`

Execution 规则：

- `case_input.yaml`、`case_id`、`run_id`、`hypothesis_board.yaml` 只在 execution 内物化或更新
- `triage` 明确属于 execution，不前移到 plan 阶段
- `triage + specialist + skeptic + curator` 明确必须通过 sub-agent 执行
- `entry_gate`、`accept_intake`、`intake_gate`、`dispatch_readiness`、`final_audit` 属于控制面，不 agent 化

关键规则：

- `triage_agent` 只提供 routing hint，不直接 dispatch specialist
- triage 产生的 `candidate_bug_refs`、`recommended_sop`、`recommended_investigation_paths` 只是方向建议，最终是否进入哪个 specialist 仍由 `rdc-debugger` 决定
- live runtime 由 broker 直接持有；specialist 只通过 `ownership_lease` + broker action 消费 live runtime
- `session_id`、`context_id`、`active_event_id` 不得作为跨阶段稳定主键传播
- 临时 Python / PowerShell / shell wrapper 封装 live CLI 一律视为流程偏差
- `waiting_for_specialist_brief`、`redispatch_pending`、`specialist_reinvestigation`、`skeptic_challenged` 期间，orchestrator 只能汇总与裁决，不能替 specialist 补证据
- `primary_completion_question`、`requested_artifact` 等意图字段属于 plan 输入归一化，不属于 run 级 runtime 真相
