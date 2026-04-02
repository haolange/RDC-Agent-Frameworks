# 单设备 `debug_plan` 示例

```yaml
schema_version: "1"
intent: debugger
normalized_goal: 确认 Adreno 650 上头发白化的根因并验证修复是否恢复到预期亮度
recommended_execution_entry: entry_gate
execution_readiness: ready

user_facts:
  requested_outcome: 根因 + 修复验证
  symptom_summary: 角色头发在近景局部光照下出现白化
  notes:
    - 头发局部过曝

capture_inventory:
  - capture_id: cap-anomalous-001
    role: anomalous
    access_mode: uploaded
    file_name: adreno650_hair_white.rdc
    source: user_supplied
    availability: accessible

reference_inventory:
  - reference_id: golden-hair-001
    kind: image
    source: user_supplied
    availability: accessible
    description: 头发高光应保留细节，不应整片泛白

environment_facts:
  api: Vulkan
  devices:
    - 小米 11 / Adreno 650 / Android 13
  drivers: []
  render_settings: {}

missing_inputs: []

reference_contract:
  source_kind: external_image
  source_refs:
    - reference:golden-hair-001
  verification_mode: pixel_value_check
  probe_set:
    pixels:
      - name: hair_hotspot
        x: 512
        y: 384
    regions: []
    symptoms:
      - 头发整片泛白
  acceptance:
    max_channel_delta: 0.06
    max_distance_l2: 0.10
    required_symptom_clearance: 1.0
  readiness_status: strict_ready
```
