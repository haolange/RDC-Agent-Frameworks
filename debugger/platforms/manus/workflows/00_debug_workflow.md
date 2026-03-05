
## 工作流概述

**名称：** Debugger 渲染调试工作流
**触发条件：** 用户报告渲染 Bug（白屏/黑屏/闪烁/精度异常/几何错误等）
**参与 Agent：** 9 个专家（详见下方步骤）
**知识文件路径（相对于 common/）：**
- `knowledge/spec/invariants/invariant_library.yaml`（23 个不变量）
- `knowledge/spec/taxonomy/symptom_taxonomy.yaml`（37 个症状标签）
- `knowledge/spec/taxonomy/trigger_taxonomy.yaml`（GPU 型号/驱动/API 已知问题）
- `knowledge/spec/skills/sop_library.yaml`（7 个 SOP）

---

## 工作流架构图

```
用户输入（渲染 Bug 描述 / capture 文件）
          │
          ▼
┌─────────────────────┐
│  Step 1: Team Lead  │  ← 问题接收、假设板初始化、任务分派
│  （协调者 / 入口）   │
└────────┬────────────┘
         │ 分派
         ▼
┌─────────────────────┐
│  Step 2: Triage     │  ← 症状分类（symptom_tags + trigger_tags）+ SOP 推荐
└────────┬────────────┘
         │ 分类结果 → Team Lead → 制定调查计划
         ▼
┌─────────────────────┐
│  Step 3: Capture    │  ← A/B 对比 capture，验证 Anchor
└────────┬────────────┘
         │ capture 文件 + anchor
         ▼
┌─────────────────────────────────────────────┐
│  Step 4: 并行调查阶段（Team Lead 按优先级调度）  │
│                                               │
│   4a. Pass Graph / Pipeline                   │ ← Command List / Pipeline State 分析
│   4b. Pixel / Value Forensics                 │ ← First Bad Event 定位
│   4c. Shader & IR                             │ ← HLSL/SPIR-V/ISA 分析
│   4d. Driver & Device（必要时）               │ ← API Trace + ISA 对比
│                                               │
└────────┬────────────────────────────────────┘
         │ 各 Agent RESULT → Team Lead
         ▼
┌─────────────────────┐
│  Step 5: Skeptic    │  ← 五把解剖刀审查（VALIDATED 前必须签署）
│  （质量门禁）        │
└────────┬────────────┘
         │ 签署 / 质疑 → 若质疑则返回 Step 4 补充证据
         ▼
┌─────────────────────┐
│  Step 6: Team Lead  │  ← 最终根因裁决 + 假设板更新（→ VALIDATED）
│  （裁决）           │
└────────┬────────────┘
         │
         ▼
┌──────────────────────────┐
│  Step 7: Curator         │  ← 生成 BugFull + BugCard 草稿
│  （报告 + 知识入库）      │
└────────┬─────────────────┘
         │ BugCard 草稿 → Skeptic 二次审查
         ▼
┌─────────────────────┐
│  Step 8: Skeptic    │  ← BugCard 质量签署（bugcard_skeptic_signed）
└────────┬────────────┘
         │ 签署 → Curator 执行知识库入库
         ▼
    调试完成 / 知识沉淀
```

---

## 各步骤详细说明

### Step 1 · Team Lead — 接收与初始化

**职责：** Delegate Mode 协调者，不执行任何 rd.* 工具

**动作：**
1. 接收用户问题，提取关键信息（设备型号、复现率、初步症状描述）
2. 初始化 Hypothesis Board（状态机）：
   ```
   H-001: [ACTIVE] 初始假设（由 Triage 分类后细化）
   ```
3. 发出 TASK_DISPATCH → Triage Agent

**质量要求：**
- 假设板必须记录所有假设的完整状态变迁历史
- 至少 3 条来自不同 Agent 的独立证据才能结案
- 禁止在有 ACTIVE 未处理假设的情况下结案

---

### Step 2 · Triage & Taxonomy — 症状分类

**职责：** 将用户自然语言映射为标准调试词汇

**动态加载：**
```
symptom_taxonomy.yaml + trigger_taxonomy.yaml + invariant_library.yaml + sop_library.yaml
```

**动作：**
1. 提取症状标签（symptom_tags）：从 symptom_taxonomy.yaml 标准词汇中选取
2. 提取触发标签（trigger_tags）：设备型号、驱动版本、图形 API
3. 从 trigger_taxonomy.yaml 查询该设备的 known_issues
4. 从 sop_library.yaml 匹配推荐 SOP
5. 输出 TRIAGE_RESULT → Team Lead

**质量要求：**
- 所有标签必须来自标准分类法，不得自造新标签
- 置信度 < 0.6 的分类必须标注 `low_confidence: true`

---

### Step 3 · Capture & Repro — 捕获与复现

**职责：** 设计并验证 A/B 对比捕获策略

**动作：**
1. 设计异常设备（A）和基准设备（B）的 capture 策略
2. 执行 capture，确保两侧 capture 包含相同场景的完整帧
3. 验证 Anchor 三个维度：
   - Pass 级：异常发生在哪个 RenderPass
   - 像素级：异常像素坐标 (x, y)
   - Resource 级：受影响的 Texture/Buffer ID
4. 输出 CAPTURE_RESULT → Team Lead

**质量要求：**
- A/B 两个 capture 必须同时存在
- Anchor 精确到 (Pass, event_id, pixel_coord, resource_id)

---

### Step 4a · Pass Graph / Pipeline — 渲染管线分析

**职责：** 分析 Native Command List，通过 Pipeline State / System State 差分定位异常 Event

**动作：**
1. 解析 Debug Marker 树，构建事件树（按 RT 切换点或 Debug Marker 分段）
2. 对比 A/B 帧的 Pipeline State（Shader / RT 格式 / Blend / Depth / Rasterizer）
3. 检查 System State（CB 绑定数值 / SRV 绑定 / Sampler），定位数据错误
4. 追踪资源屏障与状态转换，识别时序异常
5. 输出 PIPELINE_RESULT（含 anchor_event_id）→ Team Lead

**质量要求：**
- divergence_point 必须精确到 event_id 和 resource_id

---

### Step 4b · Pixel / Value Forensics — 像素取证

**职责：** 逆向追溯像素历史，定位 first_bad_event

**动作：**
1. 从 Anchor 像素坐标出发，逆向遍历像素历史
2. 找到最早产生异常值的 DrawCall（first_bad_event）
3. 检查 NaN/Inf/超范围值（FP16 溢出：> 65504）
4. 对比 A/B 设备在 first_bad_event 处的像素值
5. 输出 FORENSICS_RESULT → Team Lead

**质量要求：**
- first_bad_event 必须明确给出 event_id
- 异常像素的 RGBA 值必须来自实际工具输出

---

### Step 4c · Shader & IR — 着色器分析

**职责：** 定位 Shader 层的精度/逻辑问题

**动作：**
1. 拉取 first_bad_event 对应的 Shader 源码（A/B 双侧）
2. HLSL 关键字扫描（half/precision/RelaxedPrecision）
3. 分析 SPIR-V RelaxedPrecision 装饰（Adreno 设备必查）
4. 执行 Shader 单步调试，捕获中间变量值
5. 提取 suspicious_expression_fingerprint（跨 session 检索索引）
6. 输出 SHADER_IR_RESULT → Team Lead

**质量要求：**
- 必须提供 A/B Shader diff
- fingerprint 必须精确到具体代码表达式

---

### Step 4d · Driver & Device — 驱动与设备分析（按需触发）

**触发条件：** Triage 的 trigger_tags 包含特定 GPU 型号，或 Shader & IR 报告 IR 层差异

**职责：** API Trace 和 ISA 级别对比，归因到驱动层

**动作：**
1. 加载 trigger_taxonomy.yaml 中该 GPU 的 known_issues
2. 对比 A/B 设备的 API Trace（定量差异）
3. 若需要：提取 ISA 对比 Shader 编译器行为
4. 查询驱动版本历史（KB 搜索）
5. 输出 DRIVER_DEVICE_RESULT → Team Lead

**质量要求：**
- platform_attribution 必须明确归因层级（驱动版本/API实现/硬件行为）
- 不得在无直接证据情况下声称"这是驱动 Bug"

---

### Step 5 · Skeptic — 质量门禁审查（一）

**触发：** Team Lead 准备将假设推进至 VALIDATED 时

**五把解剖刀（必须逐一检验）：**
1. 相关性刀 — 证明因果性，而非相关性
2. 覆盖性刀 — 所有症状均被根因覆盖
3. 反事实刀 — 反事实实验有量化数据支撑
4. 工具证据刀 — 每个关键断言有工具输出支撑
5. 替代假设刀 — 所有竞争假设被显式 REFUTED

**若通过 → 输出 SKEPTIC_SIGN_OFF → Team Lead 执行最终裁决**
**若不通过 → 输出 SKEPTIC_CHALLENGE → 指定 Agent 补充证据 → 返回 Step 4**

---

### Step 6 · Team Lead — 最终裁决

**动作：**
1. 收集所有 RESULT + SKEPTIC_SIGN_OFF
2. 更新 Hypothesis Board（→ VALIDATED）
3. 输出最终根因结论（含违反的不变量编号）

---

### Step 7 · Knowledge Curator — 报告生成

**动作：**
1. 汇总所有 Agent 输出，生成 BugFull（Markdown，10 章结构）
2. 生成 BugCard（YAML，< 50 行，含 fingerprint 字段）
3. 去重检查（KB 搜索）
4. 提交 BugCard 草稿给 Skeptic（BugCard Hook）

---

### Step 8 · Skeptic — 质量门禁审查（二）

**触发：** Curator 提交 BugCard 草稿

**检查重点：**
- root_cause 精确到代码行/驱动版本/API 调用
- evidence_chain 可独立支撑 root_cause
- fix_verification 包含量化修复前后对比数据

**通过 → bugcard_skeptic_signed = true → Curator 执行知识库入库**

---

## 质量关键词速查

| 术语 | 含义 |
|------|------|
| `symptom_tags` | 标准症状标签（来自 symptom_taxonomy.yaml） |
| `trigger_tags` | 触发条件标签（GPU型号/驱动/API） |
| `first_bad_event` | 最早产生异常像素的 DrawCall（event_id） |
| `anchor` | Pass + 像素坐标 + resource_id 三维定位点 |
| `fingerprint` | 可疑代码表达式（跨 session 检索索引） |
| `platform_attribution` | 驱动归因结论（归因层级 + 具体原因） |
| `skeptic_signed` | Skeptic 对假设的签署状态 |
| `bugcard_skeptic_signed` | Skeptic 对 BugCard 的签署状态 |
| `VALIDATED` | 假设通过 Skeptic 审查后的最终确认状态 |

---
