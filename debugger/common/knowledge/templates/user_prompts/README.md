# 用户提交模板 (User Prompt Templates)

本目录包含用户向 RDC Debug Agent 提交调试请求时使用的 Prompt 模板。

---

## 文件索引

| 文件 | 用途 | 适用场景 |
|------|------|---------|
| [`USER_PROMPT_TEMPLATE.md`](./USER_PROMPT_TEMPLATE.md) | **完整版模板**（推荐复制此文件填写）| 所有场景 |
| [`USER_PROMPT_MINIMAL.md`](./USER_PROMPT_MINIMAL.md) | **极简版模板**（熟悉框架后使用）| 快速提交 |
| [`examples/example_single_device.md`](./examples/example_single_device.md) | 示例：单设备精度 Bug | 参考 single 模式 |
| [`examples/example_cross_device.md`](./examples/example_cross_device.md) | 示例：跨设备方向相反的精度异常 | 参考 cross_device 模式 |

---

## 模板结构速览

```
§ SESSION     调试模式声明（single / cross_device / regression）
§ SYMPTOM     视觉症状描述 + 问题截图
§ CAPTURES    .rdc 证据文件（必填）+ 基准捕获（推荐）
§ ENVIRONMENT 硬件/驱动/API 环境信息
§ REFERENCE   正确效果基准（修复验证闭环的关键输入）  ← 本框架特有
§ HINTS       专家线索（可选，用于缩小搜索范围）
§ PROJECT     项目上下文（可选，可由 project_plugin 代替）
```

---

## 三种调试模式的关键差异

| 字段 | `single` | `cross_device` | `regression` |
|------|----------|---------------|--------------|
| `ANOMALOUS_CAPTURE` | 必填 | 必填（A 侧）| 必填（当前坏版本）|
| `BASELINE_CAPTURE` | 可省略 | **必填**（B 侧正常设备）| **必填**（历史好版本）|
| `BASELINE_DEVICE` | 不填 | **必填** | 不填 |
| `REGRESSION_CONTEXT` | 不填 | 不填 | **必填** |
| `VERIFICATION_MODE` | `pixel_value_check` | `device_parity` | `regression_check` |

---

## § REFERENCE 节的设计意图

传统 GPU 调试流程存在一个"修复验证盲区"：Agent 将 Shader 改好后，
只知道"NaN 消失了"，但不知道"渲染看起来是否真的正确了"。

§ REFERENCE 节要求用户提供**正确渲染的语义基准**，使 Agent 在修复后能够：

1. 将修复后的像素值与期望范围作**量化对比**（Counterfactual Score）
2. 用多模态能力将修复后的截图与参考图作**视觉对比**
3. 给出"已修复 / 部分修复 / 未修复"的**结构化结论**，而非依赖人工眼判

> **简则**：§ CAPTURES 的 BASELINE 是"我有的正常参照"，
>           § REFERENCE 的 CORRECT 是"我期望修好后长这样"。
>           两者可以是同一张图，也可以不同。

---

## 与框架其他部分的映射关系

```
§ SESSION     → Team Lead         模式分派、调度策略
§ SYMPTOM     → Triage Agent      symptom_tags 提取、触发条件识别
§ CAPTURES    → Capture & Repro   .rdc 文件接入、A/B 环境建立
§ ENVIRONMENT → Triage + Driver   trigger_tags 提取、设备归因
§ REFERENCE   → Counterfactual    修复验证评分基准（新增闭环）
§ HINTS       → Team Lead         优先级调度、范围缩小
§ PROJECT     → project_plugin    引擎/模块上下文注入
```
