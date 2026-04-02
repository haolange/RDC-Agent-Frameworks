# 回归 `debug_plan` 示例

```yaml
schema_version: "1"
intent: debugger
normalized_goal: 判断 2026-03-10 回归是否来自最近 shader 修改，并验证修复是否回到历史好版本
recommended_execution_entry: entry_gate
execution_readiness: ready

user_facts:
  requested_outcome: 回归确认 + 修复验证
  symptom_summary: 新版本中披风阴影整体发黑
  notes:
    - 历史好版本为 build 1487

capture_inventory:
  - capture_id: cap-anomalous-001
    role: anomalous
    access_mode: uploaded
    file_name: cloak_black_current.rdc
    source: user_supplied
    availability: accessible
  - capture_id: cap-baseline-001
    role: baseline
    access_mode: uploaded
    file_name: cloak_ok_build_1487.rdc
    source: historical_good
    availability: accessible

reference_inventory:
  - reference_id: regression-black-cloak
    kind: screenshot
    source: user_supplied
    availability: accessible
    description: regression_black_cloak.png

environment_facts:
  api: Vulkan
  devices:
    - 小米 12 Pro / Adreno 740 / Android 13
  drivers: []
  render_settings: {}

missing_inputs: []

reference_contract:
  source_kind: capture_baseline
  source_refs:
    - capture:baseline
  verification_mode: regression_check
  probe_set:
    pixels:
      - name: cloak_mid
        x: 603
        y: 442
    regions: []
    symptoms:
      - 修复后必须回到 build 1487 的披风阴影表现
  acceptance:
    max_channel_delta: 0.03
    max_distance_l2: 0.06
    required_symptom_clearance: 1.0
  readiness_status: strict_ready
```
