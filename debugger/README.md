# Debugger Framework
## Invariant-Driven Rendering Debugger

Debugger 是面向 GPU 渲染 Bug 的多 Agent 调试框架。Debug 的主驱动是“正确性不变量”：把现象转化为可验证约束，围绕证据链与反事实实验推进到可裁决结论，并将过程沉淀为可复用知识。

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

---

## 核心概念速查

| 概念 | 定义 |
|------|------|
| **不变量（Invariant）** | 渲染过程中必须永远成立的约束（如“禁止 NaN/Inf 传播”） |
| **First Bad Event** | 像素历史中最早产生异常数值的 DrawCall（event_id） |
| **Anchor** | 问题定位的三维坐标（最终态）：pass + 像素坐标 + resource_id（Capture 阶段允许 resource_id=unknown，后续补全） |
| **Hypothesis Board** | Team Lead 维护的假设状态机（ACTIVE→VALIDATE→VALIDATED/REFUTED） |
| **五把解剖刀** | Skeptic Agent 的审查框架：相关性/覆盖性/反事实/工具证据/替代假设 |
| **BugCard** | 轻量 YAML 检索卡片（< 50 行），可在 `knowledge/library/bugcards/` 中全文检索 |
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
python extensions/debugger/scripts/validate_tool_contract.py --strict
```

### Sync platform mirrors from `common/agents`

```bash
python extensions/debugger/scripts/sync_platform_agents.py
```

### Session artifact contract (mandatory)

Artifacts must be written to:

- `extensions/debugger/common/knowledge/library/sessions/<session_id>/session_evidence.yaml`
- `extensions/debugger/common/knowledge/library/sessions/<session_id>/skeptic_signoff.yaml`
- `extensions/debugger/common/knowledge/library/sessions/<session_id>/action_chain.jsonl`
- `extensions/debugger/common/knowledge/library/sessions/.current_session`