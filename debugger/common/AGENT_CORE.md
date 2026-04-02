# RenderDoc/RDC GPU Debug 框架核心约束

本文档是 `RenderDoc/RDC GPU Debug` framework 的全局硬约束入口。

## 1. 平台真相与 framework 真相边界

`RDC-Agent Tools` 负责平台真相：tool catalog、runtime 生命周期、session/context/event 语义与错误面。

framework 只负责：

- `intent_gate`
- `Plan / Intake Phase -> debug_plan`
- `entry_gate`、`intake_gate`
- `triage -> specialist -> skeptic -> curator -> final_audit` 的阶段推进
- 共享 artifact / audit contract
- broker-owned staged handoff 的角色边界

## 2. 唯一运行模型

当前 framework 只承认以下模型：

- `coordination_mode = staged_handoff`
- `orchestration_mode = multi_agent`
- `live_runtime_policy = single_runtime_single_context`
- shared harness / broker 是唯一 enforcement SSOT

local 与 remote 都不再拥有不同的多 context 语义。所有平台都统一为：

- 同一 run 只有一个 live runtime
- 同一 live runtime 同时只有一个 active session
- 同一 active session 同时只有一个 active context
- broker 始终直接持有 tools process
- 被 dispatch 的 specialist 只持有逻辑 owner lease，不直接持有 process

## 3. Runtime SSOT Artifacts

`Plan / Intake Phase` 不产出 run 级 runtime artifact，也不创建 case/run。

严格 execution 从 `entry_gate` 开始；只有进入 `Audited Execution Phase` 后，run 级 live runtime 真相才允许落在以下 artifacts：

- `artifacts/runtime_session.yaml`
- `artifacts/runtime_snapshot.yaml`
- `artifacts/ownership_lease.yaml`
- `artifacts/runtime_failure.yaml`

结案所需 gate / final artifacts 仍为：

- `entry_gate.yaml`
- `intake_gate.yaml`
- `fix_verification.yaml`
- `skeptic_signoff.yaml`
- `run_compliance.yaml`

## 4. Handle 与跨阶段引用规则

跨阶段稳定主键只允许使用 framework ids，例如：`case_id`、`run_id`、`investigation_round`、`brief_id`、`evidence_id`、`action_request_id`。

以下 runtime ids 只属于 broker runtime view，不得作为跨阶段稳定主键传播：

- `session_id`
- `context_id`
- `active_event_id`
- 临时 resource / shader / pipeline handles

specialist brief、skeptic challenge、curator 结案都只允许引用：

- framework artifact ids
- `runtime_generation + snapshot_rev`

## 5. 主 Agent 越权属于流程偏差

`rdc-debugger` 在整个框架内的职责分两类：

- Plan 阶段：压缩汇总、补料、contract 生成、`debug_plan` 编译
- Execution 阶段：guard 推进、specialist 委托、阶段裁决

Plan 阶段默认允许 `rdc-debugger` 调度轻量 planning sub-agent，但只允许回收核心摘要，不得把原始中间推理和冗长问答全文回灌到主上下文。

当 workflow 处于 `waiting_for_specialist_brief`、`redispatch_pending`、`specialist_reinvestigation` 或 `skeptic_challenged` 时，`rdc-debugger` 只允许：

- 读取 brief / challenge
- 更新 `hypothesis_board.yaml`
- 记录 blocker
- 做 timeout / redispatch / request-more-input 决策`r`n- 当 specialist 长时间无回报时，明确进入 `BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT` 或等价阻断状态

禁止：

- 继续 live 调查
- 替 specialist 补调查
- 抢写 specialist 证据
- 通过临时 wrapper 批处理 live CLI

违反时必须在 `action_chain.jsonl` 记为 `PROCESS_DEVIATION_MAIN_AGENT_OVERREACH`。

## 6. Sub-Agent 分层

Plan 阶段默认通过以下轻量 sub-agent 收敛输入：

- `clarification_agent`
- `reference_contract_agent`
- `plan_compiler_agent`

它们的硬边界是：

- 不创建 case/run
- 不接触 live runtime
- 不写 `action_chain.jsonl`、`session_evidence.yaml`、`skeptic_signoff.yaml`
- 不进入 broker-owned execution flow

Execution 阶段只有以下节点明确必须经由 sub-agent：

- `triage`
- 所有正式 `specialist`
- `skeptic`
- `curator`

以下节点属于控制面，不 agent 化：

- `entry_gate`
- `accept_intake`
- `intake_gate`
- `dispatch_readiness`
- `dispatch_specialist`
- `specialist_feedback`
- `final_audit`
- `render_user_verdict`

## 7. 失败与恢复策略

失败分类固定为：

- `TOOL_CONTRACT_VIOLATION`
- `TOOL_RUNTIME_FAILURE`
- `TOOL_CAPABILITY_LIMIT`
- `INVESTIGATION_INCONCLUSIVE`

恢复策略固定为：

- 只有 `TOOL_RUNTIME_FAILURE` 允许 broker 做一次受控恢复
- 恢复成功后 `runtime_generation + 1`
- 连续性只允许判定为 `reattached_equivalent`、`reattached_shifted`、`reattach_failed`
- 无法证明连续性时必须 blocker

## 8. Session 真相方向

当前仓库仍保留 `.current_session` 兼容路径，但它不应继续被视为新任务默认真相来源。

后续实现应统一转向以下优先顺序：

1. `run_root`
2. `run.yaml.session_id`
3. `debug_plan`

目标是避免新 session 因共享 marker 而看到其它 case/run 产生的历史现场。
