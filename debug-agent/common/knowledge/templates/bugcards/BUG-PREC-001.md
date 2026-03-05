# BugCard: BUG-PREC-001

```yaml
bugcard_id: BUG-PREC-001
title: "Adreno 650：Local Light 解包链路 half/RelaxedPrecision 导致头发/衣物白化"

symptom_tags: [washout, local_light_unpack]
trigger_tags: [Adreno_GPU, Adreno_650, Vulkan, RelaxedPrecision]
violated_invariants: [I-PREC-01, I-LIGHT-UNPACK-01]
recommended_sop: SOP-PREC-01

root_cause_summary: >
  在 `LightGridCommon.ush:GetMobileLocalLightData` 的 local light color unpack 链路中，
  `LightData.Color = LightIntensity * DwordToUNorm(Vec1.z).xyz` 保持为 half/RelaxedPrecision 数据流，
  Adreno 650（Vulkan）在精度 lowering 后产生偏高值，导致局部光照结果过曝（白化）。

fingerprint:
  pattern: "LightData.Color = LightIntensity * DwordToUNorm(Vec1.z).xyz"
  risk_category: precision_lowering
  shader_stage: PS

fix_verified: true
fix_verification_data:
  pixel_before: {x: 512, y: 384, rgba: [0.95, 0.93, 0.90, 1.0]}
  pixel_after:  {x: 512, y: 384, rgba: [0.46, 0.44, 0.41, 1.0]}

skeptic_signed: true
bugcard_skeptic_signed: true

related_devices:
  - device: Adreno_740
    bug_card: BUG-PREC-002
    symptom_diff: "650 上白化，740 上黑化（同类 RelaxedPrecision 精度问题）"

action_chain_ref: "knowledge/traces/action_chains/example_adreno_prec.jsonl"
sop_improvement_notes: ""
```
