# RDC Debug Session Prompt — 示例：单设备精度 Bug

<!--
  示例场景：
    Adreno 650 上出现角色高光白化，无其他设备对比，
    用户提供了问题捕获和一张正常设备截图作参照。
    这是一个 single 模式的典型提交。
-->

## § SESSION
```yaml
MODE: single
TITLE: "Adreno650 角色头发高光区域白化"
PRIORITY: p1
```

## § SYMPTOM
```yaml
DESCRIPTION: |
  角色头发在强光场景中出现大面积纯白色区域（RGB 接近 1,1,1），
  正常应为浅棕/金色高光渐变。仅在 Adreno 650 上复现，
  同场景在 PC（DX12）上表现正常。
  白化区域约占头发面积的 30%，边缘锐利。

SCREENSHOT_BROKEN:
  file: hair_white_adreno650.png
  note: "Adreno 650 实机截图，帧42，头顶高光区域"

AFFECTED_REGION:
  pixel_coords: "512, 384"
  region_desc: "头顶高光聚集区，角色正面特写"

FREQUENCY: stable
```

## § CAPTURES
```yaml
ANOMALOUS_CAPTURE:
  file: capture_adreno650_frame42.rdc
  frame_hint: 42
  scene_desc: "室外场景主角特写，正午强光，静态姿态"

BASELINE_CAPTURE: ~    # 无同类设备的对照 .rdc

BASELINE_SCREENSHOT:
  file: hair_normal_pc.png
  note: "PC DX12 上的正确渲染效果，同场景同帧"
```

## § ENVIRONMENT
```yaml
AFFECTED_DEVICE:
  gpu: "Qualcomm Adreno 650"
  driver: "V@0502.0 (EV031.57.00)"
  api: vulkan
  os: "Android 12 (API 31)"
  device_model: "Xiaomi Mi 11"
```

## § REFERENCE
```yaml
CORRECT_DESCRIPTION: |
  头发高光应为浅棕/金色调，高光中心亮度约 0.5~0.7，
  向外自然衰减，不出现纯白（>0.95）或纯黑区域。
  参考 PC 截图中高光的颜色与渐变质感。

CORRECT_REFERENCE:
  file: hair_normal_pc.png
  source: "PC DX12，build v2.3.1，与问题帧相同场景"

ACCEPTABLE_DELTA:
  pixel_distance_threshold: 0.10
  coverage_threshold: 0.80

VERIFICATION_MODE: pixel_value_check
```

## § HINTS
```yaml
SUSPECTED_PASS: "MobileBasePass"
SUSPECTED_SHADER:
  - "MobileLocalLightShader.usf"
  - "GetMobileLocalLightData"
SUSPECTED_PIXELS:
  - { x: 512, y: 384, note: "最亮白化像素" }
  - { x: 495, y: 370, note: "次亮区域边缘" }
RULED_OUT:
  - "关闭 Shadow 后白化依然存在，排除阴影计算路径"
PREVIOUS_INVESTIGATION: |
  用 RenderDoc Shader 覆盖将 Fragment Shader 替换为固定颜色后白化消失，
  确认是着色器计算问题。怀疑是 half 精度在 Adreno 650 上溢出，
  未定位到具体代码行。
```

## § PROJECT
```yaml
PROJECT_NAME: "HeroGame Mobile"
ENGINE: "Unreal Engine 5.3 (custom mobile shading)"
RELEVANT_MODULES:
  - "Engine/Shaders/Private/MobileLocalLight.usf"
  - "Engine/Shaders/Private/MobileBasePassPixelShader.usf"
KNOWN_SIMILAR_BUGS:
  - BUG-PREC-001
PIPELINE_NOTES: |
  使用 Mobile Forward+，Local Light 数据通过自定义 UBO 传入，
  启用了 RelaxedPrecision decoration，历史上曾有精度相关问题。
```
