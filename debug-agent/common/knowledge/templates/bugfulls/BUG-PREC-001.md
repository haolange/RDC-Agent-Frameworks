# BugFull: BUG-PREC-001

## 1. 问题概述

- 现象：Adreno 650 上，带 local light 的场景中角色头发/衣物整体偏白（暗部缺失）；同场景 Adreno 740 正常。
- 复现率：必现。
- symptom_tags：`washout`, `local_light_unpack`
- trigger_tags：`Adreno_650`, `Vulkan`, `RelaxedPrecision`

## 2. 复现环境

- 异常侧（A）：Android / Adreno 650（A6xx）/ Vulkan / driver unknown
- 基准侧（B）：Android / Adreno 740（A7xx）/ Vulkan / driver unknown
- 引擎/渲染路径：Unreal Engine / Mobile Forward / LightGrid（Forward+ local lights）

## 3. 调试时间线

- Triage：精度类症状命中 `I-PREC-01`，推荐 `SOP-PREC-01`
- Capture：A/B 各自 capture，同场景同相机；症状在 A 可见
- Shader/IR：local light unpack 链路存在 RelaxedPrecision lowering 相关证据
- Counterfactual：unpack 后显式 cast 到 float，问题消失

## 4. 假设板历程（节选）

- H-001（`I-PREC-01`）：half/RelaxedPrecision 数据流在 A6xx 上触发精度 lowering 异常 → VALIDATED
- H-002（纹理数据错误）：A/B 同资产同路径，且在 B 正常 → REFUTED

## 5. 完整证据链（示例组织方式）

- E-001 截图对比：`artifacts/BUG-PREC-001/screenshot_compare.png`
- E-002 SPIR-V 证据：移除关键 SSA 值的 RelaxedPrecision 后恢复（示例制品：`artifacts/BUG-PREC-001/spirv_relaxedprecision_diff.txt`）
- E-003 源码锚点：`LightGridCommon.ush:GetMobileLocalLightData` 中的 color unpack 赋值链路

## 6. 反事实验证记录（量化）

- 改变变量：仅在 unpack 后插入 float cast（保持其他变量不变）
- 观测指标：同一像素坐标的 RT 输出值
- 量化结果（示例）：
  - before：`(512, 384) rgba=[0.95, 0.93, 0.90, 1.0]`
  - after ：`(512, 384) rgba=[0.46, 0.44, 0.41, 1.0]`

## 7. Skeptic 审查记录（摘要）

- 五把刀覆盖：相关性/覆盖性/反事实/工具证据/替代假设均通过
- 结论：允许推进至 VALIDATED，并允许生成 BugCard 入库

## 8. 根因结论

- violated_invariants：`I-LIGHT-UNPACK-01`, `I-PREC-01`
- 根因（精确）：在 `LightGridCommon.ush:GetMobileLocalLightData` 中，
  `LightData.Color = LightIntensity * DwordToUNorm(Vec1.z).xyz` 保持为 half/RelaxedPrecision 数据流，
  Adreno 650（Vulkan）在精度 lowering 后产生偏高值，导致局部光照结果过曝（白化）。

## 9. 修复方案

- 修复模式：Precision Fence / CastToFloat
- Patch diff（示例）：

```diff
diff --git a/LightGridCommon.ush b/LightGridCommon.ush
@@
-   LightData.Color = LightIntensity * DwordToUNorm(Vec1.z).xyz;
+   half3  LightColorUNorm_h = DwordToUNorm(Vec1.z).xyz;
+   float3 LightColorUNorm_f = (float3)LightColorUNorm_h;
+   LightData.Color = LightIntensity * LightColorUNorm_f;
```

- 验证：
  - Adreno 650：问题消失
  - Adreno 740：无回归

## 10. 知识沉淀

- BugCard：`common/knowledge/library/bugcards/bugcard_BUG-PREC-001.yaml`
- fingerprint.pattern：`LightData.Color = LightIntensity * DwordToUNorm(Vec1.z).xyz`
- related：对照案例 `BUG-PREC-002`（同类 RelaxedPrecision 精度问题，表现相反）
