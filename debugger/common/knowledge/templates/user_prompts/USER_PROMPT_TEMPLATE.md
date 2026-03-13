# RDC Debug Session Prompt — 用户提交模板（完整版）

<!--
┌─────────────────────────────────────────────────────────────────────┐
│  使用说明                                                            │
│                                                                     │
│  1. 复制本文件，按 § 顺序填写                                        │
│  2. 标记 [必填] 的字段不可省略，否则 Agent 将在启动时阻塞            │
│  3. 标记 [推荐] 的字段省略后 Agent 会降级，可能影响定位精度          │
│  4. 标记 [可选] 的字段填写越多，调试越高效，减少来回问答             │
│  5. 附件（截图、.rdc）直接附在消息中发送，路径写相对或绝对均可       │
│  6. 若有多个 .rdc 文件，在 § CAPTURES 中逐条列出                    │
└─────────────────────────────────────────────────────────────────────┘
-->

---

## § SESSION  ·  会话声明

```yaml
# 调试模式 [必填] —— 决定下游 Agent 的整体调度策略
# single:       单设备调试（一份 .rdc，无对照）
# cross_device: 跨设备对比（两份 .rdc，A=问题机 B=正常机）
# regression:   回归调试（同一设备，某个版本引入了新 Bug）
MODE: single

# 简短标题 [必填] —— 用于 case_id 前缀与报告命名
TITLE: "角色头发高光区域白化"

# 优先级 [可选] —— 影响 Skeptic 的审查严格度与报告详细程度
# p0: 线上崩溃/严重视觉破坏  p1: 主要功能受损  p2: 轻微瑕疵
PRIORITY: p1
```

---

## § SYMPTOM  ·  症状描述

```yaml
# 视觉现象文字描述 [必填]
# 写明：看到了什么 / 在哪里 / 什么情况下触发 / 严重程度
DESCRIPTION: |
  角色头发在强光照射区域出现大面积纯白色，正常情况下应呈现
  自然的金属光泽高光（浅棕/金色系）。问题仅在 Adreno 650 上
  出现，同款场景在 Adreno 740 上渲染正常。
  白化区域约占头发面积 30%，边缘锐利，非渐变。

# 问题截图附件 [必填]
# 在消息中附上截图文件，路径填相对/绝对均可
SCREENSHOT_BROKEN:
  file: broken_hair.png          # 附件文件名
  note: "截图来自 Adreno 650，帧号约 42"

# 受影响区域 [推荐] —— 帮助 Pixel Forensics Agent 快速定位
AFFECTED_REGION:
  pixel_coords: "512, 384"       # 典型异常像素坐标（屏幕坐标）
  region_desc: "角色头顶高光聚集区"

# 复现频率 [必填]
# stable:        100% 必现
# intermittent:  概率性出现（请填 probability 字段）
# one_time:      仅出现过一次
FREQUENCY: stable
# probability: 0.8   # 仅 intermittent 时填写
```

---

## § CAPTURES  ·  证据文件

<!--
[!] 没有 .rdc 文件，Agent 将立即以 BLOCKED_MISSING_CAPTURE 阻塞。
    请在发送此 Prompt 时同时附上 .rdc 文件，或填写其可访问路径。

关于 BASELINE_CAPTURE：
  - cross_device 模式：填写"正常设备"的捕获，与 ANOMALOUS 形成 A/B 对
  - regression  模式：填写"最近已知正常版本"的捕获
  - single      模式：若手头有正常设备/版本的捕获，强烈建议提供；
                      无则留空，Agent 将在纯单端模式下工作（能力降级）
-->

```yaml
# 问题捕获 [必填]
ANOMALOUS_CAPTURE:
  file: broken_adreno650.rdc     # 附件文件名或绝对路径
  frame_hint: 42                 # [推荐] 问题帧编号（不确定可省略）
  scene_desc: "室外场景，主角色站立姿态，正午强光"

# 基准捕获 [推荐 for cross_device/regression，可选 for single]
BASELINE_CAPTURE:
  file: golden_adreno740.rdc     # cross_device: 正常设备的捕获
  # file: build_v1.2.3.rdc       # regression: 历史正常版本的捕获
  frame_hint: 42                 # 与 ANOMALOUS 对应的同一帧
  scene_desc: "与问题捕获完全相同的场景和摄像机角度"

# 基准截图 [推荐] —— 无基准 .rdc 时的退路，也用于修复验证
# 即使有基准 .rdc，也建议附上截图以辅助多模态对比
BASELINE_SCREENSHOT:
  file: golden_reference.png     # 正确效果的截图（可来自正常设备/正常版本）
  note: "Adreno 740 上的正确渲染效果，头发金属高光正常"
```

---

## § ENVIRONMENT  ·  运行环境

```yaml
# 问题设备环境 [必填]
AFFECTED_DEVICE:
  gpu: "Qualcomm Adreno 650"
  driver: "V@0502.0 (EV031.xx.xx)"   # 尽量精确到子版本号
  api: vulkan                          # vulkan | d3d12 | metal | gles
  os: "Android 12 (API 31)"
  device_model: "Xiaomi 11"           # [推荐] 具体机型

# 基准设备环境 [cross_device 时必填，regression 时不适用]
BASELINE_DEVICE:
  gpu: "Qualcomm Adreno 740"
  driver: "V@0614.0 (EV031.xx.xx)"
  api: vulkan
  os: "Android 13 (API 33)"
  device_model: "Xiaomi 13"

# 回归上下文 [regression 模式时填写]
# REGRESSION_CONTEXT:
#   last_known_good: "commit: abc1234 / build: v1.2.3"
#   first_known_bad: "commit: def5678 / build: v1.3.0"
#   release_date_range: "2024-11-01 ~ 2024-11-15"
#   suspected_change: |
#     PR #1234：Shader 优化——将 float 改为 half 以提升移动端性能
```

---

## § REFERENCE  ·  修复基准

<!--
[!] 这是"修复验证闭环"的关键输入，也是本框架有别于传统调试流程的重要设计。

    Agent 修改 Shader 并重放后，需要用本节信息回答：
    "修好了"还是"没修好"——这不能只靠"值不再是 NaN"来判断，
    还需要知道"正确的渲染长什么样"。

    CORRECT_DESCRIPTION 是必须描述的；
    CORRECT_REFERENCE 文件能显著提高验证精度，强烈建议提供。
-->

```yaml
# 正确效果的文字描述 [必填]
# 写明：正确渲染的视觉特征、颜色范围、光照表现等
CORRECT_DESCRIPTION: |
  头发高光区域应呈现自然金属光泽，颜色为浅棕/金色调，
  高光亮度自然渐变，不应出现纯白（>0.95）或过暗区域。
  典型正确像素值 RGB 约在 [0.3~0.7, 0.25~0.65, 0.1~0.5] 之间。
  参考 Adreno 740 的渲染效果。

# 参考图像 [推荐]
# 可以是：正常设备截图、历史版本截图、美术设计稿、其他平台截图
CORRECT_REFERENCE:
  file: golden_reference.png     # 同 § CAPTURES 中的 BASELINE_SCREENSHOT 即可
  source: "Adreno 740 实机截图，build v1.2.3"

# 量化容差 [可选] —— 用于 Counterfactual Scoring
# 若不填，Agent 使用框架默认阈值 S ≥ 0.80
ACCEPTABLE_DELTA:
  pixel_distance_threshold: 0.08  # 修复后与基准的最大允许像素距离
  coverage_threshold: 0.85        # 修复后症状消除比例下限

# 修复验证模式 [可选]
# pixel_value_check: 验证特定像素值在目标范围内
# visual_comparison: 与参考图进行多模态对比
# device_parity:     验证问题设备输出与基准设备输出一致
# regression_check:  验证与历史正常版本输出一致
VERIFICATION_MODE: device_parity
```

---

## § HINTS  ·  专家线索  [全部可选]

<!--
这些字段是"给 Agent 的地图"——填写后可大幅缩短搜索空间。
不确定时直接省略；错误的 Hint 比没有 Hint 更糟糕。
-->

```yaml
# 可疑的 RenderPass / DrawCall 范围
SUSPECTED_PASS: "MobileBasePass"           # 或 "DeferredShadingPass" 等
SUSPECTED_DRAWCALL: ~                       # 如 "DrawCall#1247"，不确定则留 ~

# 可疑着色器模块（源码文件名或函数名）
SUSPECTED_SHADER:
  - "MobileLocalLightShader.vert"
  - "GetMobileLocalLightData()"            # 可疑函数名

# 可疑像素坐标（多个时逐条列出）
SUSPECTED_PIXELS:
  - { x: 512, y: 384, note: "头顶高光中心" }
  - { x: 488, y: 361, note: "左侧高光边缘" }

# 已排查的方向（帮助 Skeptic 不重复排查）
RULED_OUT:
  - "关闭 Shadow Map 后问题依然存在，排除阴影计算"
  - "降低分辨率至 720p 后问题依然存在，排除 MSAA"

# 此前的排查尝试（即使未得出结论，也有助于缩小范围）
PREVIOUS_INVESTIGATION: |
  尝试在 RenderDoc 中将该 DrawCall 的 Fragment Shader 替换为纯色输出，
  白化消失，进一步指向 Shader 计算问题而非资源绑定问题。
  怀疑是 half 精度溢出，但尚未定位到具体代码行。
```

---

## § PROJECT  ·  项目上下文  [可选]

<!--
若已配置 project_plugin/<project>.yaml，此节内容会自动注入，无需重复填写。
仅在未配置 project_plugin，或需要覆盖/补充其内容时填写本节。
-->

```yaml
PROJECT_NAME: "MyGame - Mobile Character Renderer"
ENGINE: "Unreal Engine 5.3 (custom mobile fork)"

# 与症状相关的代码模块（路径相对于引擎根目录）
RELEVANT_MODULES:
  - "Engine/Shaders/Private/MobileLocalLightShader.usf"
  - "Engine/Shaders/Private/MobileBasePassVertexShader.usf"
  - "Source/Runtime/Renderer/Private/MobileSceneRenderer.cpp"

# 已知的类似历史问题（可引用 BugCard ID）
KNOWN_SIMILAR_BUGS:
  - BUG-PREC-001   # Adreno 650 LocalLight half 精度白化（同类）

# 渲染管线备注
PIPELINE_NOTES: |
  使用自定义 Mobile Forward Shading，
  Local Light 数据通过 UBO 打包传递（非标准 UE5 路径），
  half 精度使用 RelaxedPrecision SPIR-V decoration。
```

---
<!--
════════════════════════════════════════════════════════════════════
  发送前自检清单
════════════════════════════════════════════════════════════════════

  [必填完整性]
  □ § SESSION.MODE 已填写
  □ § SESSION.TITLE 已填写
  □ § SYMPTOM.DESCRIPTION 已填写
  □ § SYMPTOM.FREQUENCY 已填写
  □ § CAPTURES.ANOMALOUS_CAPTURE.file 已附上 .rdc 文件
  □ § ENVIRONMENT.AFFECTED_DEVICE 已填写 gpu/driver/api/os
  □ § REFERENCE.CORRECT_DESCRIPTION 已填写

  [推荐完整性]
  □ § SYMPTOM.SCREENSHOT_BROKEN 已附上截图
  □ § CAPTURES.BASELINE_CAPTURE.file 已提供（cross_device/regression）
  □ § CAPTURES.BASELINE_SCREENSHOT.file 已附上参考截图
  □ § REFERENCE.CORRECT_REFERENCE.file 已附上正确效果图

  [模式一致性]
  □ cross_device → § CAPTURES.BASELINE_CAPTURE + § ENVIRONMENT.BASELINE_DEVICE 均已填
  □ regression  → § ENVIRONMENT.REGRESSION_CONTEXT 已填
  □ single      → 上述两项可省略

════════════════════════════════════════════════════════════════════
-->
