# 反事实评分引擎规范

反事实评分引擎（Counterfactual Scoring Engine）将「修复是否有效」从主观判断转化为可量化的评分体系。

---

## 核心概念

**反事实实验（Counterfactual Test）：** 在假设的根因上施加一个精确的干预（仅改变该因素，保持其他变量不变），观察症状是否消失。

**评分目标：** 将「干预后症状是否消失」量化为 0.0 ~ 1.0 的分数，而非主观的「看起来好多了」。

---

## 评分维度与权重

### Dimension 1：像素级恢复度（Pixel Recovery Score）

$$S_{pixel} = 1 - \frac{||pixel_{after} - pixel_{baseline}||}{||pixel_{before} - pixel_{baseline}||}$$

| 分数范围 | 含义 |
|---------|------|
| 0.90 ~ 1.00 | 完全恢复（与基准设备像素值 RMSE < 2/255） |
| 0.70 ~ 0.90 | 基本恢复（主要症状消失，存在轻微残差） |
| 0.50 ~ 0.70 | 部分恢复（症状减弱但未消失） |
| < 0.50 | 无效干预（症状未明显改善） |

**计算示例：**
```
pixel_before   = [0.21, 0.19, 0.18]  # 异常值（黑化）
pixel_baseline = [0.38, 0.35, 0.33]  # 基准设备（Mali）
pixel_after    = [0.37, 0.34, 0.32]  # 修复后

||before - baseline|| = sqrt(0.17² + 0.16² + 0.15²) = 0.277
||after  - baseline|| = sqrt(0.01² + 0.01² + 0.01²) = 0.017

S_pixel = 1 - 0.017 / 0.277 = 0.94  ✅ 完全恢复
```

### Dimension 2：变量隔离度（Variable Isolation Score）

验证干预是否仅改变了假设中的关键变量：

| 检查项 | 通过得 1 分，失败得 0 分 |
|--------|----------------------|
| 仅修改了目标变量（如 half→float），未改变其他 Shader 逻辑 | +1 |
| A/B 对比帧在相同场景、相同输入下捕获 | +1 |
| 修复前后的 DrawCall 数量相同（渲染结构未改变） | +1 |

$$S_{isolation} = \frac{\text{通过项数}}{3}$$

### Dimension 3：症状覆盖度（Symptom Coverage Score）

检查所有在 TRIAGE_RESULT 中标注的症状是否都在修复后消失：

$$S_{coverage} = \frac{\text{修复后消失的症状数}}{\text{TRIAGE_RESULT 中的症状总数}}$$

### Dimension 4：跨场景稳定性（Stability Score，可选）

在不同场景（不同光照角度、不同 draw distance）下验证修复的稳定性：

$$S_{stability} = \frac{\text{通过验证的场景数}}{\text{总验证场景数}}$$

---

## 综合评分

$$S_{counterfactual} = 0.50 \times S_{pixel} + 0.25 \times S_{isolation} + 0.20 \times S_{coverage} + 0.05 \times S_{stability}$$

（当 S_stability 不可用时，权重重新分配为 0.50 / 0.25 / 0.25 / 0.00）

---

## 通过阈值

| 场景 | 通过阈值 | 说明 |
|------|---------|------|
| 正常结案 | S_counterfactual ≥ 0.80 | 可生成 BugCard 并结案 |
| 待观察 | 0.60 ≤ S_counterfactual < 0.80 | 结案但标注 `fix_confidence: medium` |
| 驳回 | S_counterfactual < 0.60 | 反事实验证无效，不得结案，继续调查 |

---

## 记录格式（写入 Action Chain 的 evidence 字段）

```yaml
- evidence_id: "CF-001"
  type: counterfactual_test
  result: passed                          # passed / failed / inconclusive
  intervention: "half diffuse → float diffuse（第42行）"
  
  scoring:
    pixel_recovery:
      before: {x: 512, y: 384, rgba: [0.21, 0.19, 0.18, 1.0]}
      after:  {x: 512, y: 384, rgba: [0.37, 0.34, 0.32, 1.0]}
      baseline: {x: 512, y: 384, rgba: [0.38, 0.35, 0.33, 1.0]}
      score: 0.94

    variable_isolation:
      only_target_changed: true
      same_scene_same_input: true
      same_drawcall_count: true
      score: 1.00

    symptom_coverage:
      total_symptoms: 2                   # hair_darkening + banding
      recovered_symptoms: 2
      score: 1.00

    stability:
      scenes_tested: 3
      scenes_passed: 3
      score: 1.00

    total: 0.97

  conclusion: >
    反事实验证通过（S=0.97）。将第42行 half diffuse 替换为 float diffuse 后，
    像素 (512,384) 从 RGB(0.21, 0.19, 0.18) 恢复至 RGB(0.37, 0.34, 0.32)，
    与 Mali 基准设备的 RGB(0.38, 0.35, 0.33) 偏差 < 2/255，达到完全恢复标准。
    两个症状（hair_darkening 和 banding）均消失，3 个场景均通过。
```

---

## 与质量 Hook 的集成

`counterfactual_validator.py` 会检查：
- evidence 列表中是否存在 `type: counterfactual_test, result: passed` 的记录
- 是否有量化的 `scoring.total` 值（≥ 0.80）
- 是否有具体的像素值对比数据

未达到阈值的反事实验证记录将被标记为 `result: failed`，Hook 将阻止结案。
