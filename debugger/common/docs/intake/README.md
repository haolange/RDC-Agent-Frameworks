# 输入契约

本文定义 Debugger framework 唯一的用户输入合同。

目标不是规定用户必须按某种语言风格提问，而是要求任何进入调试链的输入，最终都必须被 `rdc-debugger` 规范化为同一个 `case_input.yaml`。

平台启动后默认保持普通对话态；只有用户手动召唤 `rdc-debugger`，才进入调试框架。进入框架后，由 `rdc-debugger` 自己完成 preflight、`entry_gate`、补料、intake 规范化、case/run 初始化、specialist orchestration 与受控回转。

## 0. 框架意图闸门

所有请求在进入 debugger-specific preflight、capture intake、case/run 初始化之前，必须先由 `rdc-debugger` 做 `intent_gate`。

固定规则：

- `rdc-debugger` 是唯一 framework classifier。
- A/B 可能只是 debugger 的证据方法，不自动等于 analyst。
- misroute 必须 reject + redirect，不自动代转。
- ambiguity 允许多轮澄清，且多轮期间不创建 case/run。

## 1. 双层模型

- 用户层：七段式 prompt
  - `§ SESSION`
  - `§ SYMPTOM`
  - `§ CAPTURES`
  - `§ ENVIRONMENT`
  - `§ REFERENCE`
  - `§ HINTS`
  - `§ PROJECT`
- 系统层：`case_input.yaml`
  - 这是唯一 SSOT
  - 后续 agent、validator、run artifact 只消费它，不直接消费用户原始 prose

硬规则：

- 用户提供 `.rdc` 的正式方式只有两种：在当前对话上传，或提供宿主当前会话可访问的文件路径
- accepted intake 前必须先生成 `../workspace/cases/<case_id>/artifacts/entry_gate.yaml`
- accepted intake 后由 `rdc-debugger` 创建 case/run 并把 `.rdc` 导入 `../workspace/cases/<case_id>/inputs/captures/`
- 未拿到至少一份异常 `.rdc` 前，不得创建 `case_input.yaml`
- 未拿到通过门禁的 fix reference 前，不得创建 `case_input.yaml`

## 2. `case_input.yaml` 固定结构

```yaml
schema_version: "1"
case_id: "<case_id>"

session:
  mode: single
  goal: "<一句话问题目标>"
  requested_outcome: "<用户要确认什么>"

symptom:
  summary: "<症状摘要>"
  screenshots: []
  observed_symptoms: []

captures:
  - capture_id: cap-anomalous-001
    role: anomalous
    file_name: broken.rdc
    source: user_supplied
    provenance:
      build: "<optional>"
      device: "<optional>"
      note: "<optional>"

environment:
  api: Vulkan
  devices: []
  drivers: []
  render_settings: {}

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

hints:
  suspected_modules: []
  likely_invariants: []
  notes: []

project:
  engine: Unreal
  modules: []
  branch: ""
  extra_context: []
```

规则：

- `captures` 只描述可重放 `.rdc`
- `reference_contract` 既描述语义验收合同，也描述 accepted intake 前必须通过的 fix reference readiness
- `source_refs` 只允许引用 `capture:<role>` 或 `reference:<file_id>`
- `readiness_status` 只允许：
  - `strict_ready`
  - `fallback_only`
  - `missing`
- accepted intake 前，`readiness_status` 必须为 `strict_ready`
- `visual_comparison` 只能产生 `fallback_only` 或 `missing`，不得支撑 accepted intake

## 3. 三种模式

### `single`

- 必须有一份 `role=anomalous` capture
- 必须有 `reference_contract`
- accepted intake 前必须满足 `readiness_status = strict_ready`

### `cross_device`

- 必须有 `anomalous + baseline` 两份 capture
- `reference_contract.source_kind` 必须为 `capture_baseline`
- `reference_contract.source_refs` 必须引用 `capture:baseline`
- accepted intake 前必须满足 `readiness_status = strict_ready`

### `regression`

- 必须有 `anomalous + baseline` 两份 capture
- `baseline.source` 必须为 `historical_good`
- `baseline.provenance` 必须包含 `build` 或 `revision`
- accepted intake 前必须满足 `readiness_status = strict_ready`

## 4. 输入池分层

`workspace/` 中的输入池分成两类：

```text
../workspace/cases/<case_id>/
  case_input.yaml
  inputs/
    captures/
      manifest.yaml
      <capture_id>.rdc
    references/
      manifest.yaml
      <reference_id>.png|.jpg|.md|.txt
```

硬规则：

- 用户不负责手工把 `.rdc` 预放进 `workspace/`；Agent 在 accepted intake 后导入到 `inputs/captures/`
- 导入后的原始 `.rdc` 只能放在 `inputs/captures/`
- screenshot、golden image、设计稿、验收说明只能放在 `inputs/references/`
- 不得把 reference 图混放进 capture 清单

## 5. 入口门禁

严格进入 accepted intake 的条件：

- 至少一份异常 `.rdc`
- 结构化 `reference_contract`
- `reference_contract.readiness_status = strict_ready`
- `entry_gate.yaml.status = passed`

阻断规则：

- 缺 `.rdc` -> `BLOCKED_MISSING_CAPTURE`
- 缺 fix reference 或只到 `fallback_only` -> `BLOCKED_MISSING_FIX_REFERENCE`

## 6. 配套文件

- `USER_PROMPT_TEMPLATE.md`：完整版模板
- `USER_PROMPT_MINIMAL.md`：极简骨架
- `examples/`：三种模式的填写示例
