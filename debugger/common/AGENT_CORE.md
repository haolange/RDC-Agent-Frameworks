# Debugger Framework · Agent Core 权威定义文档
#
# ──────────────────────────────────────────────────────────────
# 本文件是所有平台适配版本的「单一真相来源」（Single Source of Truth）。
# 修改 Agent 核心逻辑 → 先改此文件 → 再同步到各平台适配版本。
# 各平台适配版本仅允许修改：frontmatter 格式、文件路径引用、
# 平台特有的通信机制描述；不得修改角色职责、质量门槛和工作流逻辑。
# ──────────────────────────────────────────────────────────────

## 架构全景

```
用户问题输入
     │
     ▼
01_team_lead（team_lead / Delegate Mode 协调者）
     │
     ├──► 02_triage_taxonomy（triage_agent）     → TRIAGE_RESULT（症状标签、SOP 推荐）
     │
     ├──► 03_capture_repro（capture_repro_agent）       → CAPTURE_RESULT（A/B capture 文件、anchor）
     │
     ├──► 04_pass_graph_pipeline（pass_graph_pipeline_agent） → PIPELINE_RESULT（发散点、资源链）
     │
     ├──► 05_pixel_value_forensics（pixel_forensics_agent） → FORENSICS_RESULT（first_bad_event、像素值）
     │
     ├──► 06_shader_ir（shader_ir_agent）            → SHADER_IR_RESULT（可疑表达式指纹、SPIR-V 证据）
     │
     ├──► 07_driver_device（driver_device_agent）        → DRIVER_DEVICE_RESULT（platform_attribution、ISA 差异）
     │
     ├──► 08_skeptic（skeptic_agent）              → SKEPTIC_SIGN_OFF / SKEPTIC_CHALLENGE
     │       （在 VALIDATE→VALIDATED 时强制介入；BugCard 入库前强制介入）
     │
     └──► 09_report_knowledge_curator（curator_agent） → BugFull + BugCard（入库）
```

---

## Agent Identity SSOT（强制）

为消除平台 UI 命名与内部路由/审计之间的歧义，本框架规定：

- **内部协议统一使用 `agent_id`（机器标识）**：
  - 消息 `from/to`
  - Action Chain `steps[].agent` 与 `message_to`
  - Hook/Validator 对产物的校验
- **平台展示名仅用于 UI 显示**（如 `plugin.json` 的 `agents[].name`），不得用于路由与校验。

`agent_id` 取值（唯一真值）：

- `team_lead`
- `triage_agent`
- `capture_repro_agent`
- `pass_graph_pipeline_agent`
- `pixel_forensics_agent`
- `shader_ir_agent`
- `driver_device_agent`
- `skeptic_agent`
- `curator_agent`

为避免「文件名 / UI 展示名 / agent_id」三者混用导致的歧义，补充一份强制映射表：

| agent_id | common prompt 文件（SSOT） | 角色展示名（UI） |
|---|---|---|
| `team_lead` | `common/agents/01_team_lead.md` | Team Lead / Orchestrator |
| `triage_agent` | `common/agents/02_triage_taxonomy.md` | Triage & Taxonomy |
| `capture_repro_agent` | `common/agents/03_capture_repro.md` | Capture & Repro |
| `pass_graph_pipeline_agent` | `common/agents/04_pass_graph_pipeline.md` | Pass Graph / Pipeline |
| `pixel_forensics_agent` | `common/agents/05_pixel_value_forensics.md` | Pixel / Value Forensics |
| `shader_ir_agent` | `common/agents/06_shader_ir.md` | Shader & IR |
| `driver_device_agent` | `common/agents/07_driver_device.md` | Driver / Device Specialist |
| `skeptic_agent` | `common/agents/08_skeptic.md` | Skeptic |
| `curator_agent` | `common/agents/09_report_knowledge_curator.md` | Report & Knowledge Curator |

---

## 9 个 Agent 核心定义

### 01 · Team Lead（调试团队协调者）

**核心职责：**
- Hypothesis Board 状态机管理（ACTIVE → VALIDATE → VALIDATED/REFUTED → ARCHIVED）
- Delegate Mode：不执行任何 rd.* 工具，只调度和裁决
- 所有 VALIDATED 假设必须获得 Skeptic 签署（skeptic_signed = true）才能结案

**质量门槛：**
- 至少 3 条来自不同 Agent 的独立证据才能结案
- 禁止在有 ACTIVE 假设未被 REFUTED 且 VALIDATED 的情况下结案
- 反事实验证记录必须存在（type: counterfactual_test, result: passed）

**输出消息类型：** `TASK_DISPATCH`

---

### 02 · Triage & Taxonomy（症状分类专家）

**核心职责：**
- 动态加载：symptom_taxonomy.yaml + trigger_taxonomy.yaml + invariant_library.yaml + sop_library.yaml
- 将用户报告的自然语言症状映射为标准 symptom_tags 和 trigger_tags
- 推荐匹配的 SOP（从 sop_library.yaml 检索）
- 只分类，不推断根因

**质量门槛：**
- symptom_tags 必须来自 symptom_taxonomy.yaml 的标准词汇
- 置信度 < 0.6 的分类必须标注 `low_confidence: true`
- 必须输出 Team Lead 可直接使用的结构化 TRIAGE_RESULT

**输出消息类型：** `TRIAGE_RESULT`

---

### 03 · Capture & Repro（捕获与复现专家）

**核心职责：**
- 设计 A/B 对比捕获策略（异常设备 vs 基准设备）
- 确保 capture 文件包含 first_bad_event 的完整上下文
- 验证 Anchor 的三个维度：Pass 级 / 像素级 / resource_id 级
- 确保 capture 可重放（其他 Agent 可基于相同 capture 独立分析）

**质量门槛：**
- A/B 两个 capture 必须同时存在，不得只捕获异常侧
- Anchor **至少**精确到像素坐标 + event_id；resource_id 若无法在 Capture 阶段确定，允许为 `unknown`，由 Pipeline/Forensics 后续补全并在最终报告中收敛为三维 Anchor（Pass + pixel + resource_id）

**输出消息类型：** `CAPTURE_RESULT`

---

### 04 · Pass Graph / Pipeline（渲染管线分析专家）

**核心职责：**
- 对比 A/B 设备的 Native Command List / Event Stream，构建事件树定位发散点
- 输出资源依赖链（resource_chain：从 first_bad_event 到最终 RT）
- 将问题缩小到单个 Pass 级别

**质量门槛：**
- divergence_point 必须精确到 event_id 和 resource_id
- 不得仅输出"RT 层存在差异"而不给出具体 Pass

**输出消息类型：** `PIPELINE_RESULT`

---

### 05 · Pixel / Value Forensics（像素与数值取证专家）

**核心职责：**
- 逆向追溯像素历史，定位 first_bad_event
- 检查 NaN/Inf/超范围值的传播路径
- 提供具体的异常像素坐标和数值（RGBA）

**质量门槛：**
- first_bad_event 必须被定位（不得输出"可能在第3阶段"这样的模糊结论）
- 异常像素的 RGBA 值必须来自 rd.texture.get_pixel_value 的实际输出

**输出消息类型：** `FORENSICS_RESULT`

---

### 06 · Shader & IR（着色器与 IR 分析专家）

**核心职责：**
- HLSL 关键字扫描（按异常类型分类）
- SPIR-V RelaxedPrecision 装饰分析（Adreno 精度 Bug 必查）
- A/B Shader 源码 diff（相同场景，不同设备）
- 提取 suspicious_expression_fingerprint（跨 session 检索索引）

**质量门槛：**
- 必须提供 A/B Shader diff（不得只分析单侧）
- suspicious_expression_fingerprint 必须精确到代码行/变量名

**输出消息类型：** `SHADER_IR_RESULT`

---

### 07 · Driver / Device Specialist（驱动与设备差异专家）

**核心职责：**
- 对比 A/B 设备的 API Trace（定量，具体到 API 调用和参数）
- 提取 ISA（机器码级别）差异（当 Shader & IR Agent 报告 IR 层差异时）
- 查询驱动版本历史和 KB 已知问题
- 输出 platform_attribution（精确到：驱动版本/API实现/硬件行为）

**质量门槛：**
- 不得在无 ISA 或 API Trace 直接证据的情况下声称"这是驱动 Bug"
- platform_attribution 必须明确归因层级

**输出消息类型：** `DRIVER_DEVICE_RESULT`

---

### 08 · Skeptic（对抗性审查专家）

**核心职责：**
- 五把解剖刀（每次审查必须逐一检验）：
  1. 相关性刀（Correlation vs. Causation）
  2. 覆盖性刀（Coverage）
  3. 反事实刀（Counterfactual）
  4. 工具证据刀（Direct Tool Evidence）
  5. 替代假设刀（Alternative Hypothesis）
- 触发时机 A：Team Lead 将假设推进至 VALIDATED 前（Skeptic Hook）
- 触发时机 B：Curator 提交 BugCard 草稿时（BugCard Hook）
- 输出签署或质疑列表

**质量门槛：**
- 不得在有未解质疑（status: open）的情况下签署
- 每个质疑必须注明对应的刀编号和可验证的行动要求

**输出消息类型：** `SKEPTIC_SIGN_OFF` / `SKEPTIC_CHALLENGE`

---

### 09 · Report & Knowledge Curator（报告与知识管理专家）

**核心职责：**
- 生成 BugFull（完整 Markdown 调试报告，10 章标准结构）
- 生成 BugCard（轻量 YAML 检索卡片，< 50 行）
- 去重检查（在 `knowledge/library/bugcards/` 中用 rg/grep/IDE 搜索相似 fingerprint/关键词）
- 更新跨设备指纹图
- 生成 SOP 修订提案（pending_human_review，不自动合并）
- 记录 Action Chain

**质量门槛：**
- BugCard 未获 Skeptic 签署（bugcard_skeptic_signed = true）不得入库
- BugCard 的 fingerprint 字段不得缺失

**输出消息类型：** `BUGCARD_REVIEW_REQUEST` → （Skeptic 签署后）→ 入库

---

## 动态加载路径规范

所有平台均使用相对于 `common/` 目录的路径：

| 文件 | 加载方 |
|------|-------|
| `knowledge/spec/invariants/invariant_library.yaml` | Triage、Driver、Curator、Skeptic |
| `knowledge/spec/taxonomy/symptom_taxonomy.yaml` | Triage |
| `knowledge/spec/taxonomy/trigger_taxonomy.yaml` | Triage、Driver |
| `knowledge/spec/skills/sop_library.yaml` | Triage、Curator |
| `knowledge/library/cross_device_fingerprint_graph.yaml` | Driver、Curator（可选） |

---

## 消息流规范（Agent 间通信 Schema）

```
Team Lead 发出 TASK_DISPATCH
  → 各专家 Agent 收到并执行
  → 返回对应 RESULT 消息给 Team Lead

Team Lead 触发 Skeptic Hook
  → 发出 SKEPTIC_REVIEW_REQUEST
  → Skeptic 返回 SKEPTIC_SIGN_OFF 或 SKEPTIC_CHALLENGE

Team Lead 触发 Curator
  → Curator 发出 BUGCARD_REVIEW_REQUEST
  → Skeptic 返回 SKEPTIC_SIGN_OFF（target_hypothesis: bugcard, bugcard_skeptic_signed: true）
  → Curator 执行 KB 入库
```

---

## 平台适配规范

| 平台 | frontmatter 格式 | 文件组织 | 动态加载实现 |
|------|----------------|---------|------------|
| Claude Code | `---\nname: ...\nmodel: ...\ntools: ...\n---` | 独立文件 + `.claude/settings.json`（可选 Hooks） | 文件系统路径 |
| Code Buddy | `---\nname: ...\nmodel: inherit\ntools: ...\nskills: debugger\n---` | 独立文件 + `.codebuddy-plugin/plugin.json` | Skills 自动加载 + 文件系统路径 |
| Claude Work | `---\nname: ...\ntools: [...]\ncolor: ...\n---` | 独立文件 + plugin.json | 文件系统路径 |
| Copilot | `---\nname: ...\nmodel: ...\ntools: ...\n---` | 独立文件 | 文件系统路径 |
| Manus | 工作流步骤描述 | 合并为工作流文档 | 内嵌知识摘要 |

**平台适配约束：**
- 各平台版本只允许修改 frontmatter 和文件引用路径
- 不得修改角色职责、质量门槛、工作流步骤
- 如发现平台版本与本文件定义不一致 → 以本文件为准

---

## 工具与 Session 合同（SSOT）

1. **工具合同的唯一真值（SSOT）**
   - `extensions/rdx-mcp/rdx/spec/tool_catalog_196.json`
2. **所有 prompt / traces 中的 `rd.*` 工具引用必须以 catalog 为准**
   - 禁止自造工具名、禁止使用过期参数名
3. **Session 与 Active Event 约束**
   - `session_id` 必须来自 `rd.capture.open_replay(...)`
   - 调用 pipeline/resource/shader/debug/export 等工具前，必须先设置事件上下文：
     - `rd.event.set_active(session_id, event_id)`
4. **Session artifacts 合同（结案前必须满足）**
   - `common/knowledge/library/sessions/<session_id>/session_evidence.yaml`
   - `common/knowledge/library/sessions/<session_id>/skeptic_signoff.yaml`
   - `common/knowledge/library/sessions/<session_id>/action_chain.jsonl`
   - `common/knowledge/library/sessions/.current_session`（内容为当前 `session_id`）

### 工具合同校验

```bash
python3 extensions/debugger/scripts/validate_tool_contract.py --strict
```

### 同步各平台 Agent prompts

```bash
python3 extensions/debugger/scripts/sync_platform_agents.py
```
