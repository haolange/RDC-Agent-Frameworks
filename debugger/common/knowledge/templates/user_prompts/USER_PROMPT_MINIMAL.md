# RDC Debug Session Prompt — 极简快速版

<!--
适用场景：你熟悉框架，只需要一个快速填写的骨架。
完整字段说明见 USER_PROMPT_TEMPLATE.md。
-->

## § SESSION
```yaml
MODE: single          # single | cross_device | regression
TITLE: "<一句话描述问题>"
PRIORITY: p1          # p0 | p1 | p2
```

## § SYMPTOM
```yaml
DESCRIPTION: |
  <视觉上看到了什么？在哪里？>

SCREENSHOT_BROKEN:
  file: <broken.png>

AFFECTED_REGION:
  pixel_coords: "<x, y>"

FREQUENCY: stable     # stable | intermittent | one_time
```

## § CAPTURES
```yaml
ANOMALOUS_CAPTURE:
  file: <broken.rdc>
  frame_hint: ~

BASELINE_CAPTURE:          # cross_device/regression 时填；single 时可省略
  file: <golden.rdc>
  frame_hint: ~

BASELINE_SCREENSHOT:
  file: <golden.png>       # 正确效果的参照图
```

## § ENVIRONMENT
```yaml
AFFECTED_DEVICE:
  gpu: "<GPU 型号>"
  driver: "<驱动版本>"
  api: vulkan              # vulkan | d3d12 | metal | gles
  os: "<OS 版本>"

# BASELINE_DEVICE:         # cross_device 时取消注释
#   gpu: "<正常设备 GPU>"
#   driver: "<驱动版本>"
#   api: vulkan
#   os: "<OS 版本>"
```

## § REFERENCE
```yaml
CORRECT_DESCRIPTION: |
  <正确渲染应该长什么样？颜色范围、光照特征等>

CORRECT_REFERENCE:
  file: <golden.png>       # 与 BASELINE_SCREENSHOT 同文件即可
```

## § HINTS  _(全部可选，不确定就留空)_
```yaml
SUSPECTED_PASS: ~
SUSPECTED_SHADER: ~
SUSPECTED_PIXELS: ~
PREVIOUS_INVESTIGATION: ~
```
