# `debug_plan` Contract

`debug_plan` 是 debugger `Plan / Intake Phase` 的唯一正式输出，也是 `Plan -> Audited Execution` 的唯一交接对象。

它不是 run artifact，不属于 case/run 目录，也不代表 broker runtime 真相。

## 结构

```yaml
schema_version: "1"
intent: debugger
normalized_goal: "<一句话目标>"
recommended_execution_entry: entry_gate
execution_readiness: ready

user_facts:
  requested_outcome: "<用户想确认什么>"
  symptom_summary: "<自然语言摘要>"
  notes: []

capture_inventory:
  - capture_id: cap-anomalous-001
    role: anomalous
    access_mode: uploaded
    file_name: broken.rdc
    source: user_supplied
    availability: accessible

reference_inventory:
  - reference_id: reference-001
    kind: image
    source: user_supplied
    availability: accessible
    description: "<可选说明>"

environment_facts:
  api: Vulkan
  devices: []
  drivers: []
  render_settings: {}

missing_inputs: []

reference_contract:
  source_kind: capture_baseline
  source_refs:
    - capture:baseline
  verification_mode: device_parity
  probe_set:
    pixels: []
    regions: []
    symptoms: []
  acceptance:
    max_channel_delta: 0.05
    max_distance_l2: 0.08
    required_symptom_clearance: 1.0
  readiness_status: strict_ready

plan_summary:
  clarification_rounds: 1
  planning_agents:
    - clarification_agent
    - reference_contract_agent
    - plan_compiler_agent
  execution_notes: []
```

## 规则

- `intent` 当前只允许 `debugger`
- `recommended_execution_entry` 当前固定为 `entry_gate`
- `execution_readiness` 只允许：
  - `ready`
  - `needs_input`
  - `blocked`
- `reference_contract.readiness_status` 只允许：
  - `strict_ready`
  - `fallback_only`
  - `missing`
- 只有同时满足以下条件时，`execution_readiness` 才允许为 `ready`
  - 至少一份 `role=anomalous` capture 可访问
  - `reference_contract.readiness_status = strict_ready`
  - `missing_inputs = []`

## 边界

- `debug_plan` 不创建 case/run
- `debug_plan` 不包含 runtime ids 真相
- `debug_plan` 不代替 `case_input.yaml`
- `case_input.yaml` 由 execution 阶段根据 `debug_plan` 物化生成
