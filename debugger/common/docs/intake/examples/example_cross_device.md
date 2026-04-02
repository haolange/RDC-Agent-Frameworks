# 跨设备 `debug_plan` 示例

```yaml
schema_version: "1"
intent: debugger
normalized_goal: 对比 Adreno 740 与 Mali G99 的同场景表现，确认设备差异根因
recommended_execution_entry: entry_gate
execution_readiness: ready

user_facts:
  requested_outcome: 设备归因 + 修复验证
  symptom_summary: Adreno 740 上头发发黑，Mali G99 正常
  notes:
    - 已确认摄像机和光照设置一致

capture_inventory:
  - capture_id: cap-anomalous-001
    role: anomalous
    access_mode: uploaded
    file_name: adreno740_black.rdc
    source: user_supplied
    availability: accessible
  - capture_id: cap-baseline-001
    role: baseline
    access_mode: uploaded
    file_name: mali_g99_ok.rdc
    source: user_supplied
    availability: accessible

reference_inventory:
  - reference_id: screenshot-001
    kind: screenshot
    source: user_supplied
    availability: accessible
    description: adreno740_black.png
  - reference_id: screenshot-002
    kind: screenshot
    source: user_supplied
    availability: accessible
    description: mali_g99_ok.png

environment_facts:
  api: Vulkan
  devices:
    - 小米 12 Pro / Adreno 740 / Android 13
    - Redmi K60 / Mali G99 / Android 13
  drivers: []
  render_settings: {}

missing_inputs: []

reference_contract:
  source_kind: capture_baseline
  source_refs:
    - capture:baseline
  verification_mode: device_parity
  probe_set:
    pixels:
      - name: hair_shadow
        x: 512
        y: 384
    regions:
      - name: hair_cluster
        rect: {x: 480, y: 320, w: 96, h: 96}
    symptoms:
      - 异常侧输出应与基准设备在目标像素和目标区域保持可接受一致
  acceptance:
    max_channel_delta: 0.04
    max_distance_l2: 0.08
    required_symptom_clearance: 1.0
  readiness_status: strict_ready
```
