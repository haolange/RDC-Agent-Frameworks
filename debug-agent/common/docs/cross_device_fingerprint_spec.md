# 跨设备指纹图谱规范

跨设备指纹图谱（Cross-Device Fingerprint Graph）记录同一 Bug 模式在不同 GPU 设备上的表现差异，用于：
1. 快速识别「已知指纹在新设备上的新表现」（缩短调试时间）
2. 为 Triage Agent 提供设备特定的先验假设
3. 量化不同 GPU 驱动编译器行为的系统性差异

---

## 数据结构定义

### 顶层：Fingerprint Cluster（指纹聚类）

```yaml
fingerprint_cluster_id: "FPC-PREC-001"          # 格式：FPC-<类别>-<序号>
description: "Adreno RelaxedPrecision 精度降低类问题"
linked_invariant: "I-PREC-01"                    # 关联的 AIRD 不变量
shader_fingerprint_pattern: "half .+ = dot\\(.+, .+\\) \\* .+\\.\\w"  # 正则，用于检索
risk_level: CRITICAL                             # CRITICAL / HIGH / MEDIUM / LOW
created_at: "2026-02-27"
last_updated: "2026-02-27"
```

### 中层：Device Entry（设备条目）

```yaml
device_entries:
  - device_id: "Adreno_650_Android12"           # 格式：<GPU>_<OS>
    gpu: "Adreno 650"
    driver_version_range: ">=500.0 <512.0"
    os: "Android 12"
    api: "Vulkan 1.1"
    bugcard_id: "BUG-PREC-001"
    symptom: "hair_whitening"                   # 症状描述（symptom_taxonomy.yaml 中的标签）
    symptom_direction: positive_overflow         # positive_overflow / negative_overflow / truncation / nan
    observed_pixel_value: {x: 512, y: 384, rgba: [1.0, 1.0, 1.0, 1.0]}  # 异常像素值
    baseline_pixel_value: {x: 512, y: 384, rgba: [0.38, 0.35, 0.33, 1.0]}
    isa_behavior: "VMAD.f16（FP16 激进降级）"
    confirmed_at: "2025-11-15"

  - device_id: "Adreno_740_Android13"
    gpu: "Adreno 740"
    driver_version_range: ">=512.0"
    os: "Android 13"
    api: "Vulkan 1.3"
    bugcard_id: "BUG-PREC-002"
    symptom: "hair_blackening"                  # 同指纹，不同方向！
    symptom_direction: negative_overflow
    observed_pixel_value: {x: 512, y: 384, rgba: [0.21, 0.19, 0.18, 1.0]}
    baseline_pixel_value: {x: 512, y: 384, rgba: [0.38, 0.35, 0.33, 1.0]}
    isa_behavior: "VMAD.f16（FP16 激进降级，截断方向不同）"
    confirmed_at: "2026-02-27"
```

### 底层：Cross-Device Delta（跨设备差异分析）

```yaml
cross_device_delta:
  - dimension: "symptom_direction"
    analysis: "精度损失方向随驱动版本变化：Adreno 650 上溢出→白化；Adreno 740 上截断→黑化。根因相同（FP16 精度不足），但溢出/截断方向取决于驱动编译器的 FP16 实现细节。"
    implication: "在 Adreno 设备上发现任何方向的头发着色异常，均应优先检查 RelaxedPrecision 精度问题。"

  - dimension: "spirv_decoration"
    adreno_650: "RelaxedPrecision on OpFMul for diffuse"
    adreno_740: "RelaxedPrecision on OpFMul for specular + diffuse"
    mali_baseline: "无 RelaxedPrecision 装饰"
    analysis: "Mali 参考设备无 RelaxedPrecision，ISA 编译为 FP32，不受影响。"

  - dimension: "fix_portability"
    analysis: "将 half 替换为 float（Float_Replacement 修复模板）在两个 Adreno 版本上均有效，修复方案跨设备可移植。"

driver_attribution: "compiler_precision_lowering"
recommended_sop: "SOP-PREC-01"
```

---

## 完整示例：FPC-PREC-001

```yaml
fingerprint_cluster_id: "FPC-PREC-001"
description: "Adreno RelaxedPrecision 光照精度降低类问题"
linked_invariant: "I-PREC-01"
shader_fingerprint_pattern: "half \\w+ = dot\\("
risk_level: CRITICAL

device_entries:
  - device_id: "Adreno_650_Android12"
    gpu: "Adreno 650"
    driver_version_range: ">=500.0 <512.0"
    os: "Android 12"
    api: "Vulkan 1.1"
    bugcard_id: "BUG-PREC-001"
    symptom: "hair_whitening"
    symptom_direction: positive_overflow
    observed_pixel_value: {x: 512, y: 384, rgba: [1.0, 1.0, 1.0, 1.0]}
    baseline_pixel_value: {x: 512, y: 384, rgba: [0.38, 0.35, 0.33, 1.0]}
    isa_behavior: "VMAD.f16（FP16 激进降级）"
    confirmed_at: "2025-11-15"

  - device_id: "Adreno_740_Android13"
    gpu: "Adreno 740"
    driver_version_range: ">=512.0"
    os: "Android 13"
    api: "Vulkan 1.3"
    bugcard_id: "BUG-PREC-002"
    symptom: "hair_blackening"
    symptom_direction: negative_overflow
    observed_pixel_value: {x: 512, y: 384, rgba: [0.21, 0.19, 0.18, 1.0]}
    baseline_pixel_value: {x: 512, y: 384, rgba: [0.38, 0.35, 0.33, 1.0]}
    isa_behavior: "VMAD.f16（FP16 激进降级，截断方向不同）"
    confirmed_at: "2026-02-27"

cross_device_delta:
  - dimension: "symptom_direction"
    analysis: "精度损失方向随驱动版本变化；根因相同，症状方向不同。"
    implication: "Adreno 设备上任何头发着色异常均优先排查 RelaxedPrecision。"
  - dimension: "fix_portability"
    analysis: "Float_Replacement 修复方案跨两个 Adreno 版本均有效。"

driver_attribution: "compiler_precision_lowering"
recommended_sop: "SOP-PREC-01"
```

---

## 指纹图谱维护规则

1. **新建 Cluster**：当 Curator Agent 生成新 BugCard 时，检查 `suspicious_expression_fingerprint` 是否与已有 Cluster 的 `shader_fingerprint_pattern` 匹配。若匹配，添加新 Device Entry；若不匹配，新建 Cluster。

2. **版本控制**：每次更新后增加 `last_updated` 字段，不修改历史 Device Entry（只追加）。

3. **存放路径**：`common/knowledge/library/cross_device_fingerprint_graph.yaml`

4. **索引格式**：文件顶层保留 `cluster_index`（按 `linked_invariant` 分组的快速索引），供 Triage Agent 和 Driver Agent 快速检索。

---

## 与其他组件的关系

| 组件 | 关系 |
|------|------|
| `invariant_library.yaml` | 每个 Cluster 必须关联至少一个不变量（`linked_invariant`） |
| `sop_library.yaml` | 每个 Cluster 的 `recommended_sop` 与 SOP 库 ID 一一对应 |
| `Triage Agent` | 加载此文件，在 trigger_tags 匹配时提供已知 Cluster 作为先验假设 |
| `Driver Agent` | 加载此文件，在新 session 中查询当前指纹是否命中已知 Cluster |
| `Curator Agent` | 每次生成 BugCard 后，更新此文件（添加 Device Entry 或新建 Cluster） |
