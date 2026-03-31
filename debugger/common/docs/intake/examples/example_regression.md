# 回归示例

```text
§ SESSION
MODE: regression
GOAL: 判断 2026-03-10 回归是否来自最近 shader 修改，并验证修复是否回到历史好版本
REQUESTED_OUTCOME: 回归确认 + 修复验证

§ SYMPTOM
SUMMARY: 新版本中披风阴影整体发黑
SCREENSHOTS:
  - regression_black_cloak.png

§ CAPTURES
ANOMALOUS_CAPTURE:
  FILE: cloak_black_current.rdc
  SOURCE: user_supplied
BASELINE_CAPTURE:
  FILE: cloak_ok_build_1487.rdc
  SOURCE: historical_good
  NOTE: build=1487

§ ENVIRONMENT
API: Vulkan
DEVICES:
  - 小米 12 Pro / Adreno 740 / Android 13

§ REFERENCE
SOURCE_KIND: capture_baseline
SOURCE_REFS:
  - capture:baseline
VERIFICATION_MODE: regression_check
CORRECT_DESCRIPTION:
  - 修复后必须回到 build 1487 的披风阴影表现
PROBE_SET:
  PIXELS:
    - name: cloak_mid
      x: 603
      y: 442
ACCEPTANCE:
  max_channel_delta: 0.03
  max_distance_l2: 0.06
  required_symptom_clearance: 1.0
  fallback_only: false

§ HINTS
NOTES:
  - 历史好版本为 build 1487

§ PROJECT
ENGINE: Unreal
MODULES:
  - Cloak shading
  - Mobile lighting
```
