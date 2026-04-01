# 工作区布局契约

本文定义 debugger framework 的 `workspace/` 合同。

`workspace/` 只承载本次运行的输入、gate artifact、notes、screenshots 与对外交付；共享真相仍在 `common/`。

## 1. 分层

- `common/`
  - 共享真相与平台配置
- `workspace/`
  - case/run 运行区

硬规则：

- 运行期截图、capture、notes、reports 不回写 `common/`
- 共享 spec、role、config 不写进 `workspace/`
- 第二层 deliverable 只能派生自第一层证据，不能反向改写共享真相
- 并行 case 只能共享仓库，不得共享同一条 live `context`

## 2. 相对路径约定

平台模板引用运行区时，统一使用：

- `../workspace`

## 3. Case / Run 目录

```text
workspace/
  cases/
    <case_id>/
      case.yaml
      artifacts/
        entry_gate.yaml
      case_input.yaml
      inputs/
        captures/
          manifest.yaml
          <capture>.rdc
        references/
          manifest.yaml
      runs/
        <run_id>/
          run.yaml
          capture_refs.yaml
          artifacts/
            intake_gate.yaml
            runtime_topology.yaml
            fix_verification.yaml
            runtime_batons/
            remote_prerequisite_gate.yaml
            remote_capability_gate.yaml
            remote_recovery_decision.yaml
          logs/
          notes/
            hypothesis_board.yaml
            remote_planning_brief.yaml
            remote_runtime_inconsistency.yaml
          screenshots/
          reports/
            report.md
            visual_report.html
```

## 4. Gate Artifact Rules

- `.rdc` 是创建 case 的硬前置；未拿到 `.rdc` 不创建 case/run
- `fix reference` 是创建 run 的硬前置；未拿到 `strict_ready` 的 `reference_contract` 不进入 accepted intake
- `entry_gate.yaml` 是 case 级 preflight / capture / fix-reference 权威 gate
- `intake_gate.yaml` 是 run 级 accepted intake 权威 gate
- `runtime_topology.yaml` 是 run 级 runtime / locality / owner / baton / loop round 权威 artifact
- `fix_verification.yaml` 是 run 级修复验证唯一权威 artifact

新增硬规则：

- remote run 必须显式落盘 remote 专属 gate artifact
- 无 `fix_verification.yaml` 不得进入 skeptic
- 无 skeptic strict signoff 不得进入 curator
- 无 curator 最终写入不算 finalized
- `fallback_only` / `missing` 的 reference readiness 不得通过 `entry_gate` 或 `intake_gate`

## 5. Runtime Topology Required Fields

`runtime_topology.yaml` 至少要表达：

- `workflow_stage`
- `entry_mode`
- `backend`
- `coordination_mode`
- `orchestration_mode`
- `single_agent_reason`
- `delegation_status`
- `fallback_execution_mode`
- `remote_context_locality`
- `remote_handle_origin_context`
- `remote_handle_reuse_policy`
- `remote_gate_status`
- `remote_capability_matrix`
- `blocked_capability_codes`
- `recovery_policy`
- `investigation_round`
- `redispatch_count`
- `last_challenge_source`
- `last_timeout_at`

## 6. Intake Gate Required Fields

`intake_gate.yaml` 至少要表达：

- `reference_readiness`
- `clarification_required`
- `redispatch_allowed`
- `accepted_for_live_investigation`

## 7. Fix Verification Required Fields

`fix_verification.yaml` 至少要表达：

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

`fix_verification.yaml` 只承载真正进入验证阶段后的结果，不承载补料中的临时 reference 状态。

## 8. Notes And Report Rules

- `notes/hypothesis_board.yaml` 是 orchestration 控制状态源
- specialist brief 必须写入 `notes/**`
- remote 规划与不一致说明必须写成结构化 notes
- `reports/report.md` / `reports/visual_report.html` 是对外交付层，不是第一层真相

`hypothesis_board.yaml` 至少固定展示：

- `current_loop_reason`
- `evidence_gap_summary`
- `last_specialist_round`
- `remaining_retry_budget`

## 9. Write Scope

共享 write scope 只允许：

- `workspace_control`
  - `case.yaml`
  - `case_input.yaml`
  - `inputs/captures/manifest.yaml`
  - `inputs/references/manifest.yaml`
  - `run.yaml`
  - `capture_refs.yaml`
  - `notes/hypothesis_board.yaml`
- `workspace_notes`
  - `runs/<run_id>/artifacts/**`
  - `runs/<run_id>/notes/**`
  - `runs/<run_id>/screenshots/**`
- `workspace_reports`
  - `reports/report.md`
  - `reports/visual_report.html`
- `session_signoff`
  - `common/knowledge/library/sessions/<session_id>/skeptic_signoff.yaml`
- `session_artifacts`
  - `common/knowledge/library/sessions/.current_session`
  - `common/knowledge/library/sessions/<session_id>/session_evidence.yaml`
  - `common/knowledge/library/sessions/<session_id>/action_chain.jsonl`
- `knowledge_library`
  - `common/knowledge/library/**`
  - `common/knowledge/proposals/**`

角色边界：

- `rdc-debugger` 只写 `workspace_control`
- specialists 只写 `workspace_notes`
- `skeptic_agent` 只写 `session_signoff`
- `curator_agent` 只写 `workspace_reports`、`session_artifacts` 与 `knowledge_library`
