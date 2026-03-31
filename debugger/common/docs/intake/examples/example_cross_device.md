# 跨设备示例

```text
§ SESSION
MODE: cross_device
GOAL: 对比 Adreno 740 与 Mali G99 的同场景表现，确认设备差异根因
REQUESTED_OUTCOME: 设备归因 + 修复验证

§ SYMPTOM
SUMMARY: Adreno 740 上头发发黑，Mali G99 正常
SCREENSHOTS:
  - adreno740_black.png
  - mali_g99_ok.png

§ CAPTURES
ANOMALOUS_CAPTURE:
  FILE: adreno740_black.rdc
  SOURCE: user_supplied
BASELINE_CAPTURE:
  FILE: mali_g99_ok.rdc
  SOURCE: user_supplied

§ ENVIRONMENT
API: Vulkan
DEVICES:
  - 小米 12 Pro / Adreno 740 / Android 13
  - Redmi K60 / Mali G99 / Android 13

§ REFERENCE
SOURCE_KIND: capture_baseline
SOURCE_REFS:
  - capture:baseline
VERIFICATION_MODE: device_parity
CORRECT_DESCRIPTION:
  - 修复后异常侧输出应与基准设备在目标像素和目标区域保持可接受一致
PROBE_SET:
  PIXELS:
    - name: hair_shadow
      x: 512
      y: 384
  REGIONS:
    - name: hair_cluster
      rect: {x: 480, y: 320, w: 96, h: 96}
ACCEPTANCE:
  max_channel_delta: 0.04
  max_distance_l2: 0.08
  required_symptom_clearance: 1.0
  fallback_only: false

§ HINTS
NOTES:
  - 已确认摄像机和光照设置一致

§ PROJECT
ENGINE: Unreal
MODULES:
  - Hair shading
```
