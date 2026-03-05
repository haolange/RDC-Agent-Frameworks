# AIRD Framework
## AI-Driven Invariant-Reasoning Debugger 

AIRD（AI-Driven Invariant-Reasoning Debugger）是面向 GPU 渲染 Bug 的多 Agent 调试框架。它通过形式化的**不变量推理**（Invariant Reasoning）和**多专家协作**，将复杂渲染问题的调试流程标准化、可追溯、可自我进化。

> 设计目标：让 AI Agent 能够像资深渲染工程师一样，系统性地排查「同设备正常、异设备异常」的跨平台渲染 Bug。

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                                           │
├─────────────────┬───────────────────────────────────────────┤
│   知识层（M1）   │  Agent 层（M2/M3）                         │
│                 │                                             │
│  knowledge/spec/│  common/agents/   ← 9 个平台无关核心 Prompt │
│                 │  platforms/       ← 5 个平台适配版本        │
├─────────────────┼───────────────────────────────────────────┤
│  质量层（M4）   │  自进化层（M5）                              │
│                 │                                             │
│  hooks/         │  docs/            ← 4 个规范文档            │
│  .claude/       │  knowledge/       ← library/traces/templates│
├─────────────────┴───────────────────────────────────────────┤
│                  项目适配层（M6）                              │
│  project_plugin/  ← Plugin 规范 + 示例                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 快速上手

### 0. 安装（可选：启用 Quality Hooks 时需要）

Quality Hooks（M4）依赖 Python 3 + PyYAML：
```bash
python3 -m pip install -r common/hooks/requirements.txt
```

### 1. 选择平台

| 你的工作环境 | 使用路径 |
|------------|---------|
| Claude Code（命令行） | `platforms/claude-code/agents/` |
| Code Buddy（腾讯云代码助手） | `platforms/code-buddy/` + `.codebuddy-plugin/plugin.json` |
| Claude Work（桌面插件） | `platforms/claude-work/` + `plugin.json` |
| GitHub Copilot | `platforms/copilot/agents/` |
| Manus | `platforms/manus/workflows/00_debug_workflow.md` |

### 2. 加载知识库

在 Agent 会话开始时，确保以下文件可被访问（动态加载）：
```
common/knowledge/spec/invariants/invariant_library.yaml   # 23 个不变量
common/knowledge/spec/taxonomy/symptom_taxonomy.yaml      # 37 个症状标签
common/knowledge/spec/taxonomy/trigger_taxonomy.yaml      # GPU/驱动/API 已知问题
common/knowledge/spec/skills/sop_library.yaml             # 7 个 SOP
```

### 3. 加载 Project Plugin（可选但推荐）

将你的项目信息写入 Plugin 文件：
```
common/project_plugin/<你的项目名>.yaml
```
参考 `PLUGIN_SPEC.md` 和 `example_mobile_game.yaml`。

### 4. 启动调试

向 Team Lead 发送问题描述：
```
设备：Adreno 740（Android 13）
症状：角色头发着色偏黑，同场景在 Mali-G99 上正常
复现率：100%（所有头发材质角色）
```

Team Lead 将自动调度 Triage → Capture → 并行专家分析 → Skeptic 审查 → 报告生成。

---

## 模块详解

### M1 · 知识层

| 文件 | 内容 |
|------|------|
| `common/knowledge/spec/invariants/invariant_library.yaml` | 23 个渲染不变量，含症状标签、检测工具、修复模式 |
| `common/knowledge/spec/taxonomy/symptom_taxonomy.yaml` | 37 个标准症状标签，含分类、优先级、示例 |
| `common/knowledge/spec/taxonomy/trigger_taxonomy.yaml` | GPU 型号、驱动版本、图形 API 的已知问题映射 |
| `common/knowledge/spec/skills/sop_library.yaml` | 7 个标准操作程序，含工具链、反事实规范、修复模板 |

### M2 · Agent 核心层

9 个专家 Agent，每个包含：动态加载声明 · 完整工作流 · 质量门槛检查清单 · 结构化输出 Schema · 禁止行为列表

| Agent | 职责 | 输出消息类型 |
|-------|------|------------|
| 01 Team Lead | Delegate Mode 协调，假设板状态机 | `TASK_DISPATCH` |
| 02 Triage & Taxonomy | 症状分类，SOP 推荐 | `TRIAGE_RESULT` |
| 03 Capture & Repro | A/B 对比捕获，Anchor 验证 | `CAPTURE_RESULT` |
| 04 Pass Graph / Pipeline | Native Command List / Event Stream 发散点定位 | `PIPELINE_RESULT` |
| 05 Pixel Forensics | first_bad_event 逆向追溯 | `FORENSICS_RESULT` |
| 06 Shader & IR | HLSL/SPIR-V/ISA 分析，代码指纹 | `SHADER_IR_RESULT` |
| 07 Driver & Device | API Trace + ISA 对比，驱动归因 | `DRIVER_DEVICE_RESULT` |
| 08 Skeptic | 五把解剖刀审查，双重签署门禁 | `SKEPTIC_SIGN_OFF` / `SKEPTIC_CHALLENGE` |
| 09 Report & Knowledge Curator | BugFull + BugCard 生成，知识库入库 | `BUGCARD_REVIEW_REQUEST` |

权威定义：`common/AGENT_CORE.md`

### M3 · 多平台适配层

5 个平台，语义 100% 一致，格式按平台规范适配。详见 `docs/多平台适配说明.md`。

### M4 · Quality Hooks 系统

```
common/hooks/
├── README.md                        # 系统说明与扩展指南
├── validators/
│   ├── bugcard_validator.py         # BugCard 12 项完整性检查
│   ├── counterfactual_validator.py  # 反事实验证记录检查
│   └── skeptic_signoff_checker.py   # Skeptic 五把刀签署验证
└── schemas/
    ├── bugcard_required_fields.yaml
    └── skeptic_signoff_schema.yaml
```

Claude Code 平台通过 `.claude/settings.json` 实现系统级强制；其他平台通过 Prompt 层质量门槛降级实现。

### M5 · 自进化基础设施

| 文件 | 用途 |
|------|------|
| `common/docs/action_chain_schema.yaml` | 调试 session 的完整工具调用序列记录格式 |
| `common/docs/sop_extraction_guide.md` | 从 Action Chain 半自动提取 SOP 草稿的操作规范 |
| `common/docs/cross_device_fingerprint_spec.md` | 跨设备指纹图谱（同 Bug 在不同 GPU 上的表现关联） |
| `common/docs/counterfactual_scoring_spec.md` | 反事实验证量化评分体系（0~1.0，阈值 0.80） |
| `common/knowledge/traces/action_chains/` | 历史调试案例（`.jsonl` 格式，可用于 SOP 提取） |
| `common/knowledge/library/` | 知识库与会话产物目录（BugCard 入库、BugFull 输出、指纹图/索引，可选但推荐） |

### M6 · Project Plugin

```
common/project_plugin/
├── PLUGIN_SPEC.md              # Plugin 接口规范
└── example_mobile_game.yaml   # 完整示例（虚构移动游戏项目）
```

---

## 核心概念速查

| 概念 | 定义 |
|------|------|
| **不变量（Invariant）** | 渲染过程中必须永远成立的约束（如「禁止 NaN/Inf 传播」） |
| **First Bad Event** | 像素历史中最早产生异常值的 DrawCall（event_id） |
| **Anchor** | 问题定位的三维坐标（最终态）：Pass + 像素坐标 + resource_id（Capture 阶段允许 resource_id=unknown，后续补全） |
| **Hypothesis Board** | Team Lead 维护的假设状态机（ACTIVE→VALIDATE→VALIDATED/REFUTED） |
| **五把解剖刀** | Skeptic Agent 的审查框架：相关性/覆盖性/反事实/工具证据/替代假设 |
| **BugCard** | 轻量 YAML 检索卡片（< 50 行），可在 `knowledge/library/bugcards/` 中全文检索（rg/grep/IDE 搜索） |
| **BugFull** | 完整 Markdown 调试报告（10 章结构），供工程师阅读 |
| **Action Chain** | 完整调试 session 的工具调用和决策序列记录（`.jsonl`） |
| **Fingerprint** | 可疑代码表达式的结构化描述，用于跨 session 匹配同类 Bug |
| **Project Plugin** | 项目级知识注入接口（材质模块、项目不变量、资源映射） |

---

## Tool Contract SSOT and Sync Workflow

`common/` is the only editable source for agent prompts and contract rules.
Do not manually edit platform prompt mirrors.

### Validate contract drift (strict)

```bash
python extensions/debug-agent/scripts/validate_tool_contract.py --strict
```

### Sync platform mirrors from `common/agents`

```bash
python extensions/debug-agent/scripts/sync_platform_agents.py
```

### Session artifact contract (mandatory)

Artifacts must be written to:

- `extensions/debug-agent/common/knowledge/library/sessions/<session_id>/session_evidence.yaml`
- `extensions/debug-agent/common/knowledge/library/sessions/<session_id>/skeptic_signoff.yaml`
- `extensions/debug-agent/common/knowledge/library/sessions/<session_id>/action_chain.jsonl`
- `extensions/debug-agent/common/knowledge/library/sessions/.current_session`
