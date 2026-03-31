# BugCard：BUG-PREC-001

```yaml
bugcard_id: BUG-PREC-001
title: "Adreno 650：Local Light 解包链路 half/RelaxedPrecision 导致头发/衣物白化"

symptom_tags: [washout, local_light_unpack]
trigger_tags: [Adreno_GPU, Adreno_650, Vulkan, RelaxedPrecision]
violated_invariants: [I-PREC-01, I-LIGHT-UNPACK-01]
recommended_sop: SOP-PREC-01
causal_anchor_type: first_bad_event
causal_anchor_ref: "event:523"
causal_chain_summary: >
  目标像素在 Event#523 首次出现过曝；同一 drawcall 的 local light unpack 表达式在 Adreno 650 上经
  RelaxedPrecision lowering 后产生偏高值，因此白化是在该 drawcall 引入，而不是在后续 screen-like pass 首次可见。

root_cause_summary: >
  在 `LightGridCommon.ush:GetMobileLocalLightData` 的 local light color unpack 链路中，
  `LightData.Color = LightIntensity * DwordToUNorm(Vec1.z).xyz` 保持为 half/RelaxedPrecision 数据流，
  Adreno 650（Vulkan）在精度 lowering 后产生偏高值，导致局部光照结果过曝。

fingerprint:
  pattern: "LightData.Color = LightIntensity * DwordToUNorm(Vec1.z).xyz"
  risk_category: precision_lowering
  shader_stage: PS

fix_verified: true
verification:
  reference_contract_ref: "../workspace/cases/case-adreno650-white/case_input.yaml#reference_contract"
  structural:
    status: passed
    artifact_ref: "../workspace/cases/case-adreno650-white/runs/run-001/artifacts/fix_verification.yaml#structural_verification"
  semantic:
    status: passed
    artifact_ref: "../workspace/cases/case-adreno650-white/runs/run-001/artifacts/fix_verification.yaml#semantic_verification"

skeptic_signed: true
bugcard_skeptic_signed: true

related_devices:
  - device: Adreno_740
    bug_card: BUG-PREC-002
    symptom_diff: "650 上白化，740 上黑化（同类 RelaxedPrecision 精度问题）"

action_chain_ref: "common/knowledge/library/sessions/session-03rdc-debug-001/action_chain.jsonl"
sop_improvement_notes: ""
```
