# 输入契约

本文定义 Debugger framework 唯一的用户输入合同。

目标不是规定用户必须按某种语言风格提问，而是要求任何进入调试链的输入，最终都必须被 `rdc-debugger` 规范化为同一个 `case_input.yaml`。

平台启动后默认保持普通对话态；只有用户手动召唤 `rdc-debugger`，才进入调试框架。进入框架后，由 `rdc-debugger` 自己完成 preflight、`entry_gate`、补料、intake 规范化、case/run 初始化与 specialist orchestration。

## 0A. 最小非交互式预检

当宿主运行的是类似 `claude -p` 的非交互式提示，或者提示只是在做冒烟式就绪检查时，`rdc-debugger` 可以使用 `preflight_mode: minimal_non_interactive`。

`minimal_non_interactive` 模式必须：

- stop after `intent_gate`
- stop after `entry_gate`
- stop after setup verification
- stop after capture presence check
- declare the chosen entry mode
- return bounded readiness output

`minimal_non_interactive` 模式不得：

- normalize full intake
- dispatch specialists
- create `case/run`
- write `case_input.yaml`
- write `hypothesis_board.yaml`
- continue inside `rdc-debugger`

完整的 `case/run` 创建仍然要以已接受的 `rdc-debugger` intake 和已通过的 `entry_gate` 为前提。

## 0. 框架意图闸门

所有请求在进入 debugger-specific preflight、capture intake、case/run 初始化之前，必须先由 `rdc-debugger` 做 `intent_gate`。

固定规则：

- `rdc-debugger` 是唯一 framework classifier。
- A/B 可能只是 debugger 的证据方法，不自动等于 analyst。
- misroute 必须 reject + redirect，不自动代转。
- ambiguity 允许多轮澄清，且多轮期间不创建 case/run。

固定边界：

- 主完成问题是“哪里不同”，且没有 root-cause / fix-verification 目标：转 `rdc-analyst`
- 主完成问题是性能、预算、瓶颈、收益：转 `rdc-optimizer`
- A/B 只是为了证明 bug 原因或 fix 是否成立：仍可属于 `debugger`

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
- 未拿到至少一份异常 `.rdc` 前，`rdc-debugger` 只能在当前会话 / 主面板中维护补料状态，不得创建 case/run 或 `hypothesis_board.yaml`
- `intent_gate` 在 run 创建前只存在于当前会话；只有 `decision=debugger` 且 run 已创建后，才把摘要写进 `hypothesis_board.yaml`
- 七段式 prompt 可以省略部分说明，但 `rdc-debugger` 必须把缺失项显式归一化为 `unknown`、`[]` 或模式级阻断错误
- `case_input.yaml` 只能在 capture intake 成功后写入 `../workspace/cases/<case_id>/`

## 2. `case_input.yaml` 固定结构

```yaml
schema_version: "1"
case_id: "<case_id>"

session:
  mode: single                       # single | cross_device | regression
  goal: "<一句话问题目标>"
  requested_outcome: "<用户要确认什么>"

symptom:
  summary: "<症状摘要>"
  screenshots: []
  observed_symptoms: []

captures:
  - capture_id: cap-anomalous-001
    role: anomalous                  # anomalous | baseline | fixed
    file_name: broken.rdc
    source: user_supplied            # user_supplied | historical_good | generated_counterfactual
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
  source_kind: capture_baseline      # capture_baseline | external_image | design_spec | mixed
  source_refs:
    - capture:baseline
  verification_mode: device_parity   # pixel_value_check | device_parity | regression_check | visual_comparison
  probe_set:
    pixels: []
    regions: []
    symptoms: []
  acceptance:
    max_channel_delta: 0.05
    max_distance_l2: 0.08
    required_symptom_clearance: 1.0
    fallback_only: false

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
- `reference_contract` 只描述语义验收合同，不等同于某个 capture
- `source_refs` 只允许引用 `capture:<role>` 或 `reference:<file_id>`
- `visual_comparison` 只能产生 `fallback_only` 语义验证，不得支撑严格结案

## 3. 三种模式

### `single`

- 必须有一份 `role=anomalous` capture
- 必须有 `reference_contract`
- 若 `reference_contract` 只有图片/描述，没有量化 probe，则只允许 `fallback_only=true`

### `cross_device`

- 必须有 `anomalous + baseline` 两份 capture
- `reference_contract.source_kind` 必须为 `capture_baseline`
- `reference_contract.source_refs` 必须引用 `capture:baseline`
- 默认 `verification_mode=device_parity`

### `regression`

- 必须有 `anomalous + baseline` 两份 capture
- `baseline.source` 必须为 `historical_good`
- `baseline.provenance` 必须包含 `build` 或 `revision`
- 默认 `verification_mode=regression_check`

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
- `inputs/captures/manifest.yaml` 是导入 provenance 的唯一 SSOT，至少记录：
  - `capture_id`
  - `file_name`
  - `capture_role`
  - `source`
  - `import_mode`
  - `imported_at`
  - `sha256`
  - `source_path`（仅 `import_mode=path` 时记录）
- 上传导入不得伪造 `source_path`；应记录等价上传来源标识
- `case_input.yaml` 不镜像导入路径、hash 或导入时间；这些字段只保留在 capture manifest
- `capture_refs.yaml` 只记录 run 实际采用的 capture 引用与 provenance 摘要，不回写导入源细节
- accepted intake 后必须立即生成 `runs/<run_id>/artifacts/intake_gate.yaml`
- 调查启动前必须生成 `runs/<run_id>/artifacts/runtime_topology.yaml`
- `intake_gate.yaml` 通过前，不得进入 specialist dispatch 或 live `rd.*` 调试
- `dispatch`、`tool_execution`、`artifact_write`、`quality_check` 的 payload 必须带上 `entry_mode`、`backend`、`context_id`、`runtime_owner`、`baton_ref`

## 5. 严格验证与 fallback 验证

严格验证要求：

- `structural_verification.status = passed`
- `semantic_verification.status = passed`
- `reference_contract.acceptance.fallback_only = false`

fallback 验证允许：

- 调试继续推进
- 生成报告
- 记录 symptom coverage

fallback 验证禁止：

- `fix_verified=true`
- BugCard 入库
- strict finalization

## 6. 配套文件

- `USER_PROMPT_TEMPLATE.md`：完整版模板
- `USER_PROMPT_MINIMAL.md`：极简骨架
- `examples/`：三种模式的填写示例
