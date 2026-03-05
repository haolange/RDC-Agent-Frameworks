# BugCard 模板（入库格式）

> 权威规范：`common/hooks/schemas/bugcard_required_fields.yaml`
>
> 推荐文件名包含 `bugcard` 以触发平台 Hook，例如：`common/knowledge/library/bugcards/bugcard_BUG-XXX-001.yaml`

```yaml
bugcard_id: BUG-XXX-001
title: "<一句话描述（10~120字）>"

symptom_tags: [washout]
trigger_tags: [Adreno_GPU, Vulkan]
violated_invariants: [I-PREC-01]
recommended_sop: SOP-PREC-01

root_cause_summary: >
  <精确根因描述：必须包含代码位置或驱动版本或 API 调用，禁止“可能是/大概”类表述。>

fingerprint:
  pattern: "<可疑表达式/调用签名>"
  risk_category: "<precision_overflow|precision_lowering|nan_propagation|...>"
  shader_stage: PS

fix_verified: true
fix_verification_data:
  pixel_before: {x: 0, y: 0, rgba: [0.0, 0.0, 0.0, 1.0]}
  pixel_after:  {x: 0, y: 0, rgba: [0.0, 0.0, 0.0, 1.0]}

skeptic_signed: true
bugcard_skeptic_signed: true

# 可选字段
related_devices: []
action_chain_ref: ""
sop_improvement_notes: ""
```
