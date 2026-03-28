# Truth Store Contract

本文定义 debugger framework 在文件系统上的真相存储合同。

本合同只规定 artifact 角色、寻址、引用与单写者边界；不引入 object store / database 抽象，也不替代底层 Tools 的持久化实现。

## 1. 五类共享真相 Artifact

### `action_chain.jsonl`

- 角色：`append_only_ledger`
- 记录：run/session 中发生过什么
- 规则：只允许 append，不允许改写历史

### `session_evidence.yaml`

- 角色：`adjudicated_snapshot`
- 记录：已裁决的 `causal_anchor`、`hypotheses`、`counterfactual_reviews`、`reference_contract` 与 `fix_verification` 摘要
- 规则：单写者快照，重写时 `snapshot_version` 必须单调递增

### `registry/active_manifest.yaml`

- 角色：`versioned_spec_pointer`
- 记录：当前生效 spec 版本
- 规则：只能由 spec 演化流程切换

### `evolution_ledger.jsonl`

- 角色：`append_only_governance_ledger`
- 记录：knowledge candidate 的发射、验证、shadow、激活、回滚
- 规则：只允许 append

### `run_compliance.yaml`

- 角色：`derived_audit`
- 记录：run 级审计结果
- 规则：是派生物，不得反向覆盖上游事实

## 2. Workspace Artifact As Gate Inputs

以下对象不属于共享知识库真相，但属于 finalization 必需输入：

- `case_input.yaml`
- `entry_gate.yaml`
- `intake_gate.yaml`
- `runtime_topology.yaml`
- `fix_verification.yaml`
- `skeptic_signoff.yaml`

remote run 额外要求：

- `remote_prerequisite_gate.yaml`
- `remote_capability_gate.yaml`
- `remote_recovery_decision.yaml`
- `notes/remote_planning_brief.yaml`
- `notes/remote_runtime_inconsistency.yaml`

补充说明：

- `rd.session.get_context.preview` 不是 gate input。
- preview 只允许作为人类同步观察状态；不得替代 `runtime_topology.yaml`、`fix_verification.yaml` 或 `session_evidence.yaml`。

## 3. Required Cross References

- `session_evidence.yaml` 必须记录 `spec_snapshot_ref` 与 `active_spec_versions`
- `session_evidence.reference_contract.ref` 必须指回 `case_input.yaml#reference_contract`
- `session_evidence.fix_verification.ref` 必须指回 `artifacts/fix_verification.yaml`
- report 只能引用已存在于 ledger、snapshot、workspace artifact 或 active spec snapshot 中的结构化对象

## 4. Action Chain Required Audit Fields

涉及 gate / dispatch / artifact_write / skeptic / curator / deviation 的事件，必须可审计以下字段：

- `workflow_stage_transition`
- `process_deviation`
- `blocking_code`
- `required_artifacts_before_transition`
- `runtime`
- `locality`
- `owner`
- `baton`

硬规则：

- 阶段切换必须落 `workflow_stage_transition`
- 主 agent overreach 必须落 `process_deviation`
- unresolved `process_deviation` 会阻断 finalization

## 5. Fix Verification Contract

`fix_verification.yaml` 是 run 级唯一修复验证真相对象，至少包含：

- `verdict`
- `verification_mode`
- `verification_confidence`
- `blocked_by_capability`
- `blocked_capability_codes`
- `candidate_fix_prepared`
- `candidate_fix_live_applied`
- `candidate_fix_structurally_validated`
- `candidate_fix_semantically_validated`
- `structural_verification`
- `semantic_verification`
- `overall_result`

硬规则：

- `overall_result.status=passed` 时，结构与语义验证都必须是 `passed`
- `fallback_only` 不能被提升成 strict pass
- `blocked_by_capability=true` 时，`overall_result.status` 必须为 `failed`
- 不再维护旧 `fix_verification_data`

## 6. Runtime Topology Contract

`runtime_topology.yaml` 是 run 级 topology 权威对象，至少包含：

- `workflow_stage`
- `remote_capability_matrix`
- `remote_context_locality`
- `remote_handle_origin_context`
- `remote_handle_reuse_policy`
- `remote_gate_status`
- `recovery_policy`
- `blocked_capability_codes`

remote gate 与 remote truthful-fail verdict 必须基于这些字段，而不是额外猜测。

## 7. Single Writer Boundaries

- `action_chain.jsonl`
  - 多 agent 可追加，但不得修改既有事件
- `session_evidence.yaml`
  - 只允许单写者提交当前版本，默认由 `curator_agent` 负责
- `fix_verification.yaml`
  - 只允许维护一份正式修复验证对象
- `run_compliance.yaml`
  - 只允许由审计过程生成

## 8. Recovery Order

恢复顺序固定为：

1. `session_evidence.yaml`
2. `action_chain.jsonl`
3. `case_input.yaml`
4. `fix_verification.yaml`
5. `runtime_topology.yaml`
6. remote gate artifact
7. `active_manifest.yaml`
8. `evolution_ledger.jsonl`
9. `run_compliance.yaml`

## 9. Forbidden Patterns

- 不得把 `run_compliance.yaml` 当作唯一真相源回推 session 事实
- 不得在 `session_evidence.yaml` 中复制整段 tool trace
- 不得再维护旧 `fix_verification_data` 或第二套修复验证入口
- 不得为了兼容旧 schema 而双写第二套 intake / snapshot / verification 对象
- 不得把 preview 状态、窗口存活或人类观察结果写成结构化验证真相来替代 canonical `rd.*` 证据
