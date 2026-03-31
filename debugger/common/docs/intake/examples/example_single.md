# 单设备示例

```text
§ SESSION
MODE: single
GOAL: 确认 Adreno 650 上头发白化的根因并验证修复是否恢复到预期亮度
REQUESTED_OUTCOME: 根因 + 修复验证

§ SYMPTOM
SUMMARY: 角色头发在近景局部光照下出现白化
OBSERVED_SYMPTOMS:
  - 头发局部过曝
SCREENSHOTS:
  - hair_white_spot.png

§ CAPTURES
ANOMALOUS_CAPTURE:
  FILE: adreno650_hair_white.rdc
  SOURCE: user_supplied

§ ENVIRONMENT
API: Vulkan
DEVICES:
  - 小米 11 / Adreno 650 / Android 13

§ REFERENCE
SOURCE_KIND: external_image
SOURCE_REFS:
  - reference:golden-hair-001
VERIFICATION_MODE: pixel_value_check
CORRECT_DESCRIPTION:
  - 头发高光应保留细节，不应整片泛白
PROBE_SET:
  PIXELS:
    - name: hair_hotspot
      x: 512
      y: 384
ACCEPTANCE:
  max_channel_delta: 0.06
  max_distance_l2: 0.10
  required_symptom_clearance: 1.0
  fallback_only: false

§ HINTS
LIKELY_INVARIANTS:
  - I-PREC-01

§ PROJECT
ENGINE: Unreal
MODULES:
  - Local light
  - Hair shading
```
