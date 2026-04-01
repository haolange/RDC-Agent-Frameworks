# 用户输入模板

将下面七段填写后提交给 `rdc-debugger`。  
Agent 会把它规范化为 `case_input.yaml`，并据此初始化 case/run。

accepted intake 前必须同时满足两件事：

- 至少一份可导入的异常 `.rdc`
- 一份结构化且 `strict_ready` 的 `fix reference`

## § SESSION

```text
MODE: single | cross_device | regression
GOAL: 我希望 Agent 最终确认什么
REQUESTED_OUTCOME: 需要给出根因 / 修复建议 / 修复验证 / 回归确认
```

## § SYMPTOM

```text
SUMMARY: 问题一句话描述
OBSERVED_SYMPTOMS:
  - 症状 1
  - 症状 2
SCREENSHOTS:
  - 当前对话里提交的截图 / 录屏文件名
```

## § CAPTURES

```text
ANOMALOUS_CAPTURE:
  FILE: broken.rdc
  SOURCE: user_supplied
  NOTE: 异常设备 / 异常场景

BASELINE_CAPTURE:
  FILE: good.rdc
  SOURCE: historical_good | user_supplied
  NOTE: 正常设备 / 历史好版本
```

## § REFERENCE

```text
SOURCE_KIND: capture_baseline | external_image | design_spec | mixed
SOURCE_REFS:
  - capture:baseline
  - reference:golden-001
VERIFICATION_MODE: pixel_value_check | device_parity | regression_check | visual_comparison

PROBE_SET:
  PIXELS:
    - name: hair_hotspot
      x: 512
      y: 384
  REGIONS:
    - name: hair_cluster
      rect: {x: 480, y: 320, w: 96, h: 96}
  SYMPTOMS:
    - white_spot
    - blackout

ACCEPTANCE:
  max_channel_delta: 0.05
  max_distance_l2: 0.08
  required_symptom_clearance: 1.0

READINESS_STATUS: strict_ready
```

规则：

- `READINESS_STATUS` 只允许 `strict_ready | fallback_only | missing`
- accepted intake 前必须是 `strict_ready`
- 如果只有图片或文字，没有 probe / baseline / 可执行验收对象，则只能填 `fallback_only`，这会触发 `BLOCKED_MISSING_FIX_REFERENCE`
- `visual_comparison` 不能单独支撑 strict run

## § ENVIRONMENT

```text
API: Vulkan | D3D12 | Metal | OpenGL
DEVICES:
  - 设备 / GPU / OS
DRIVERS:
  - 驱动版本
RENDER_SETTINGS:
  resolution: ""
  aa: ""
  post_process: ""
```

## § HINTS

```text
SUSPECTED_MODULES:
  - 可能相关的模块 / shader / pass
LIKELY_INVARIANTS:
  - I-PREC-01
NOTES:
  - 已知线索、排查历史、禁止方向
```

## § PROJECT

```text
ENGINE: Unreal | Unity | Custom
MODULES:
  - Hair shading
  - Local light
BRANCH: ""
EXTRA_CONTEXT:
  - 项目相关背景
```

## 提交前自查

- 至少上传一份异常 `.rdc`
- `CAPTURES` 里不要放图片或设计稿
- `REFERENCE` 必须结构化，且 accepted intake 前要达到 `strict_ready`
- 只有图片/文字参考时，当前 run 会被 `BLOCKED_MISSING_FIX_REFERENCE` 阻断
