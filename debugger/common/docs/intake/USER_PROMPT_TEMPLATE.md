# 用户输入模板

将下面七段填写后提交给 `rdc-debugger`。  
Agent 会把它规范化为 `case_input.yaml`，并据此初始化 case/run。

---

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

FIXED_CAPTURE:
  FILE: fixed.rdc
  SOURCE: generated_counterfactual
  NOTE: 仅在已有修复后提交；初次调试可留空
```

填写规则：

- 只在这里填写 `.rdc`
- `single` 模式可不填 `BASELINE_CAPTURE`
- `cross_device` / `regression` 模式必须填 `BASELINE_CAPTURE`

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

## § REFERENCE

```text
SOURCE_KIND: capture_baseline | external_image | design_spec | mixed
SOURCE_REFS:
  - capture:baseline
  - reference:golden-001
VERIFICATION_MODE: pixel_value_check | device_parity | regression_check | visual_comparison

CORRECT_DESCRIPTION:
  - 正确画面应该具备的视觉特征
  - 正确颜色 / 高光 / 阴影的大致期望

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
  fallback_only: false
```

规则：

- `SOURCE_KIND` 和 `SOURCE_REFS` 决定语义基准来自哪里
- `PROBE_SET` 是 strict 验证的量化对象
- 如果只有图片或文字，没有 probe，则必须把 `fallback_only` 设为 `true`
- `visual_comparison` 只允许用于 fallback/report，不会支撑 `fix_verified=true`

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

---

## 提交前自查

- 至少上传一份异常 `.rdc`
- `CAPTURES` 里不要放图片或设计稿
- `REFERENCE` 里不要放 `.rdc` 文件路径描述为“语义说明”
- 想要 strict 修复验证时，必须提供量化 probe 或可对齐的 baseline capture
