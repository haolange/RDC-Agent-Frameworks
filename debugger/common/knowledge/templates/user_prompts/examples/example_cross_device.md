# RDC Debug Session Prompt — 示例：跨设备对比调试

<!--
  示例场景：
    同一场景在 Adreno 740 上头发变暗（变黑），
    在 Adreno 650 上却变白——两台设备都异常，方向相反。
    用户各有一份 .rdc，需要 A/B 对比定位驱动层差异。
    这是 cross_device 模式的典型提交。
-->

## § SESSION
```yaml
MODE: cross_device
TITLE: "Adreno740 vs Adreno650 头发渲染方向相反的精度异常"
PRIORITY: p0
```

## § SYMPTOM
```yaml
DESCRIPTION: |
  同一场景、同一 Shader 在两台不同 Adreno 设备上产生方向相反的渲染错误：
  - Adreno 650：头发高光区域过亮（纯白，RGB ≈ 1,1,1）
  - Adreno 740：头发高光区域过暗（纯黑，RGB ≈ 0,0,0）
  PC DX12 上渲染完全正常，是唯一的"正确基准"。
  两个设备上问题均稳定复现，无闪烁。

SCREENSHOT_BROKEN:
  file: hair_adreno650_white.png
  note: "Adreno 650：头发白化（过亮），帧42"

SCREENSHOT_BROKEN_B:
  file: hair_adreno740_black.png
  note: "Adreno 740：头发变黑（过暗），帧42"

AFFECTED_REGION:
  pixel_coords: "512, 384"
  region_desc: "角色头发高光区域，两张截图坐标一致"

FREQUENCY: stable
```

## § CAPTURES
```yaml
# A 侧：问题设备（Adreno 650，过亮）
ANOMALOUS_CAPTURE:
  file: capture_adreno650_frame42.rdc
  frame_hint: 42
  scene_desc: "室外强光，角色正面特写，静态姿态"

# B 侧：对比设备（Adreno 740，过暗）
# 注意：B 侧同样是异常的，但方向相反，可作为互相对比的参照
BASELINE_CAPTURE:
  file: capture_adreno740_frame42.rdc
  frame_hint: 42
  scene_desc: "与 A 侧完全相同的场景、帧、摄像机"

# 真正的"正确效果"参照截图（来自 PC）
BASELINE_SCREENSHOT:
  file: hair_pc_correct.png
  note: "PC DX12 正确渲染，同帧同场景，用于修复验证"
```

## § ENVIRONMENT
```yaml
# A 侧：问题设备（高光白化）
AFFECTED_DEVICE:
  gpu: "Qualcomm Adreno 650"
  driver: "V@0502.0 (EV031.57.00)"
  api: vulkan
  os: "Android 12 (API 31)"
  device_model: "Xiaomi Mi 11"

# B 侧：对比设备（高光变黑）
BASELINE_DEVICE:
  gpu: "Qualcomm Adreno 740"
  driver: "V@0614.0 (EV031.61.00)"
  api: vulkan
  os: "Android 13 (API 33)"
  device_model: "Xiaomi 13 Pro"
```

## § REFERENCE
```yaml
CORRECT_DESCRIPTION: |
  头发高光应为浅棕/金色调，高光中心亮度约 0.4~0.65，
  向外渐变自然，不出现纯白（>0.95）或纯黑（<0.05）。
  参考 PC DX12 截图：高光有明显金属质感，颜色偏暖，边缘柔和。

CORRECT_REFERENCE:
  file: hair_pc_correct.png
  source: "PC DX12，build v2.3.1，OpenGL 与 Vulkan 两端结果一致"

ACCEPTABLE_DELTA:
  pixel_distance_threshold: 0.08
  coverage_threshold: 0.85

# cross_device 模式下的最终验证目标：
# 修复后两台设备的渲染输出应与 PC 基准一致（允许有限误差）
VERIFICATION_MODE: device_parity
```

## § HINTS
```yaml
SUSPECTED_PASS: "MobileBasePass"
SUSPECTED_SHADER:
  - "MobileKajiyaKayDiffuse.usf"
  - "MobileKajiyaKayDiffuseAttenuation()"
SUSPECTED_PIXELS:
  - { x: 512, y: 384, note: "两台设备上均为最显著异常像素" }
RULED_OUT:
  - "同场景 Adreno 630 表现正常，排除所有 Adreno 设备普遍问题"
  - "降级为 OpenGL ES 3.2 后 650 白化消失，指向 Vulkan/SPIR-V 路径"
PREVIOUS_INVESTIGATION: |
  初步观察：650 白化（overflow 方向），740 变黑（underflow 方向）。
  两者在同一 Shader 上触发，推测是 half 精度在不同 GPU 上
  截断行为不同导致（正向溢出 vs 负向截断）。
  已查阅 BUG-PREC-001（650 白化）和 BUG-PREC-002（740 变黑），
  本次问题与两者高度吻合，怀疑是同类问题的新 Shader 复现。
```

## § PROJECT
```yaml
PROJECT_NAME: "HeroGame Mobile"
ENGINE: "Unreal Engine 5.3 (custom mobile shading)"
RELEVANT_MODULES:
  - "Engine/Shaders/Private/MobileKajiyaKay.usf"
  - "Engine/Shaders/Private/HairBxDF.usf"
KNOWN_SIMILAR_BUGS:
  - BUG-PREC-001   # 650 精度白化（LocalLight），同类
  - BUG-PREC-002   # 740 精度变黑（KajiyaDiffuse），高度相关
PIPELINE_NOTES: |
  头发使用自定义 Kajiya-Kay BxDF，half 精度路径全面启用。
  650 和 740 在 ISA 层对 RelaxedPrecision 的实现不同，
  历史上已有两次精度相关 Bug（见上方）。
  当前问题 Shader 路径与 BUG-PREC-002 的触发路径高度重叠。
```
