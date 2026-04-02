# Intake Contract

本文定义 debugger framework 的前置输入合同与 `debug_plan` 交接模型。

目标不再是要求用户命中某个模板或内部 schema，而是要求任何进入 debugger 的请求，最终都由 `rdc-debugger` 在 Plan 阶段规范化为同一个 `debug_plan`。用户只负责提供自然语言事实、目标和可访问材料；系统负责追问、归纳、生成 contract，并决定何时可以进入严格 execution。

## 0. 基本原则

- `rdc-debugger` 是唯一 public entrypoint 与唯一 framework classifier。
- 宿主如果支持 Plan Mode，应先运行 debugger 的 `Plan / Intake Phase`。
- Plan 阶段默认通过轻量 sub-agent 收敛输入，但 orchestrator 只保留核心简化摘要。
- ambiguity 允许多轮澄清，且澄清期间不创建 case/run。
- `strict_ready reference_contract` 是系统在 Plan 阶段生成的内部 contract，不由用户心智维护。

## 1. 双阶段模型

### `Plan / Intake Phase`

Plan 阶段负责：

- `intent_gate`
- 最小追问与补料
- capture / reference / environment 事实整理
- `reference_contract` 生成与 readiness 判定
- `debug_plan` 编译

Plan 阶段硬边界：

- 不创建 case/run
- 不写 `action_chain.jsonl`、`session_evidence.yaml`、`skeptic_signoff.yaml`
- 不接触 live runtime
- 不调用 broker-owned execution flow

### `Audited Execution Phase`

只有当 `debug_plan.execution_readiness = ready` 时，才允许进入 execution。

Execution 固定从 `entry_gate` 开始：

`entry_gate -> accept_intake / intake_gate -> triage -> dispatch/specialist loop -> skeptic -> curator -> final_audit / user_verdict`

`case_input.yaml`、case/run、runtime artifacts 都在这一阶段物化。

## 2. `debug_plan` 是唯一前置 SSOT

Plan 阶段的唯一正式输出是 `debug_plan`，后续 execution 只消费它，不直接消费用户原始 prose。

最低结构要求见 [`DEBUG_PLAN.md`](./DEBUG_PLAN.md)。

最少必须覆盖：

- `intent`
- `normalized_goal`
- `user_facts`
- `capture_inventory`
- `reference_inventory`
- `environment_facts`
- `missing_inputs`
- `reference_contract`
- `execution_readiness`
- `recommended_execution_entry`

硬规则：

- 用户提供 `.rdc` 的正式方式仍只有两种：在当前对话上传，或提供宿主当前会话可访问的文件路径
- 未拿到至少一份异常 `.rdc` 前，不得进入 execution
- `strict_ready reference_contract` 不是用户手填合同，而是 Plan 阶段的系统判定结果
- execution 前必须满足 `recommended_execution_entry = entry_gate`

## 3. `reference_contract` 定位

`reference_contract` 既描述语义验收合同，也描述 execution 前必须通过的 fix reference readiness。

规则：

- `source_refs` 只允许引用 `capture:<role>` 或 `reference:<file_id>`
- `readiness_status` 只允许：
  - `strict_ready`
  - `fallback_only`
  - `missing`
- 只有 `strict_ready` 才允许进入 execution
- `visual_comparison` 最多只能产生 `fallback_only` 或 `missing`，不得直接支撑 execution readiness

## 4. Sub-Agent 边界

Plan 阶段默认通过以下轻量 sub-agent 收敛信息：

- `clarification_agent`
- `reference_contract_agent`
- `plan_compiler_agent`

规则：

- 它们只回传核心摘要，不回传冗长问答全文和大段中间推理
- 它们不创建 case/run
- 它们不接触 live runtime
- 它们不写 run/session 审计产物

Execution 阶段只有以下节点明确必须经由 sub-agent：

- `triage`
- 所有正式 `specialist`
- `skeptic`
- `curator`

`entry_gate`、`accept_intake`、`intake_gate`、`dispatch_readiness`、`dispatch_specialist`、`specialist_feedback`、`final_audit`、`render_user_verdict` 都属于控制面，不 agent 化。

## 5. 进入 Execution 的硬条件

严格进入 execution 的条件：

- 至少一份异常 `.rdc`
- `debug_plan` 已生成
- `debug_plan.reference_contract.readiness_status = strict_ready`
- `debug_plan.execution_readiness = ready`
- 从 `entry_gate` 开始进入严格链

阻断规则：

- 缺 `.rdc` -> `BLOCKED_MISSING_CAPTURE`
- reference readiness 只有 `fallback_only` 或 `missing` -> `BLOCKED_MISSING_FIX_REFERENCE`

## 6. 配套文件

- [`DEBUG_PLAN.md`](./DEBUG_PLAN.md)：`debug_plan` 结构与语义
- [`PLAN_MODE_COMPATIBILITY.md`](./PLAN_MODE_COMPATIBILITY.md)：宿主 Plan Mode 与 debugger 的结合方式
- `examples/`：Plan 阶段产物示例
