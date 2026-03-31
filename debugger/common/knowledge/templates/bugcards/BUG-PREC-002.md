# BugCard：BUG-PREC-002

```yaml
bugcard_id: BUG-PREC-002
title: "Adreno 740：KajiyaDiffuse half/RelaxedPrecision lowering 触发负值钳零导致头发/披风黑化"

symptom_tags: [blackout, hair_shading]
trigger_tags: [Adreno_GPU, Adreno_740, Vulkan, RelaxedPrecision]
violated_invariants: [I-PREC-01, I-SHADING-NONNEG-01]
recommended_sop: SOP-PREC-01
causal_anchor_type: first_bad_event
causal_anchor_ref: "event:523"
causal_chain_summary: >
  目标像素在 Event#523 首次变坏；同一 drawcall 的 `half KajiyaDiffuse = 1 - abs(dot(N, L));`
  在 Adreno 740 上经 RelaxedPrecision lowering 后产生异常负值，因此黑化是在该 drawcall 引入，而不是在后续 pass 首次可见。

root_cause_summary: >
  在 `MobileShadingModels.ush:MobileKajiyaKayDiffuseAttenuation` 中，
  `half KajiyaDiffuse = 1 - abs(dot(N, L));` 于 Event#523 对应的 PS drawcall 上经 Adreno 740 Vulkan 编译链 lowering 后出现异常负值，
  导致头发/披风区域被错误压黑。

fingerprint:
  pattern: "half KajiyaDiffuse = 1 - abs(dot(N, L));"
  risk_category: precision_lowering
  shader_stage: PS

fix_verified: true
verification:
  reference_contract_ref: "../workspace/cases/case-adreno740-black/case_input.yaml#reference_contract"
  structural:
    status: passed
    artifact_ref: "../workspace/cases/case-adreno740-black/runs/run-001/artifacts/fix_verification.yaml#structural_verification"
  semantic:
    status: passed
    artifact_ref: "../workspace/cases/case-adreno740-black/runs/run-001/artifacts/fix_verification.yaml#semantic_verification"

skeptic_signed: true
bugcard_skeptic_signed: true

related_devices:
  - device: Adreno_650
    bug_card: BUG-PREC-001
    symptom_diff: "650 上白化，740 上黑化（同类 RelaxedPrecision 精度问题）"

action_chain_ref: "common/knowledge/library/sessions/session-03rdc-debug-001/action_chain.jsonl"
sop_improvement_notes: ""
```
