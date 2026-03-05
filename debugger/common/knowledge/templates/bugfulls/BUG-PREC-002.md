# BugFull: BUG-PREC-002

## 1. 问题概述

- 现象：Adreno 740 上，角色头发/披风整体被压到接近纯黑，细节消失；同场景 Adreno 650 正常。
- 复现率：必现。
- symptom_tags：`blackout`, `hair_shading`
- trigger_tags：`Adreno_740`, `Vulkan`, `RelaxedPrecision`

## 2. 复现环境

- 异常侧（A）：Android / Adreno 740（A7xx）/ Vulkan / driver unknown
- 基准侧（B）：Android / Adreno 650（A6xx）/ Vulkan / driver unknown
- 引擎/渲染路径：Unreal Engine / Mobile Hair Shading（Kajiya-Kay + scatter）

## 3. 调试时间线

- Triage：精度/黑化症状命中 `I-PREC-01`，推荐 `SOP-PREC-01`
- Capture：A/B capture 对齐，症状在 A 可见
- Pixel Forensics：锁定异常像素与 first_bad_event（示例）
- Shader/IR：定位到 KajiyaDiffuse half 计算链路与 RelaxedPrecision lowering 关联
- Counterfactual：将 dot(N,L) 改为 float 计算后问题消失

## 4. 假设板历程（节选）

- H-001（`I-PREC-01`）：half/RelaxedPrecision 导致 KajiyaDiffuse 计算异常 → VALIDATED
- H-002（barrier 缺失）：在对照实验中不影响目标像素 → REFUTED

## 5. 完整证据链（示例组织方式）

- E-001 截图对比：`artifacts/BUG-PREC-002/screenshot_compare.png`
- E-002 SPIR-V 证据：`OpDecorate %<id> RelaxedPrecision` 关联到 KajiyaDiffuse 链路（示例制品：`artifacts/BUG-PREC-002/spirv_relaxedprecision_slice.txt`）
- E-003 源码锚点：`MobileShadingModels.ush:MobileKajiyaKayDiffuseAttenuation`

## 6. 反事实验证记录（量化）

- 改变变量：仅将 `dot(N,L)` 的计算提升为 float（其余不变）
- 量化结果（示例）：
  - before：`(512, 384) rgba=[0.02, 0.02, 0.02, 1.0]`
  - after ：`(512, 384) rgba=[0.34, 0.32, 0.30, 1.0]`

## 7. Skeptic 审查记录（摘要）

- 五把刀覆盖：相关性/覆盖性/反事实/工具证据/替代假设均通过
- 结论：允许推进至 VALIDATED，并允许生成 BugCard 入库

## 8. 根因结论

- violated_invariants：`I-SHADING-NONNEG-01`, `I-PREC-01`
- 根因（精确）：在 `MobileShadingModels.ush:MobileKajiyaKayDiffuseAttenuation` 中，
  `half KajiyaDiffuse = 1 - abs(dot(N, L));` 在 Adreno 740（Vulkan）上经 RelaxedPrecision lowering 后出现负值/异常，
  后续非负钳位链将结果压为 0，导致头发/披风区域整体塌黑。

## 9. 修复方案

- 修复模式：CastToFloat / Precision Fence（可选 Hardening：`max(0, ...)`）
- Patch diff（示例）：

```diff
diff --git a/MobileShadingModels.ush b/MobileShadingModels.ush
@@
-   half KajiyaDiffuse = 1 - abs(dot(N, L));
+   float NoL_f = dot((float3)N, (float3)L);
+   half  KajiyaDiffuse = (half)(1.0 - abs(NoL_f));
+   // optional hardening:
+   // KajiyaDiffuse = max((half)0, KajiyaDiffuse);
```

- 验证：
  - Adreno 740：问题消失
  - Adreno 650：无回归

## 10. 知识沉淀

- BugCard：`common/knowledge/library/bugcards/bugcard_BUG-PREC-002.yaml`
- fingerprint.pattern：`half KajiyaDiffuse = 1 - abs(dot(N, L));`
- related：对照案例 `BUG-PREC-001`（同类 RelaxedPrecision 精度问题，表现相反）
