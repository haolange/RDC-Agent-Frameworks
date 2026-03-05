# AIRD Framework · Quality Hooks 系统

Quality Hooks 系统将 AIRD 框架的质量门槛从「被建议的」提升为「被强制执行的」。

---

## 架构

```
common/hooks/
├── README.md                        # 本文件：系统说明与扩展指南
├── validators/
│   ├── bugcard_validator.py         # BugCard 完整性检查（12 项规则）
│   ├── counterfactual_validator.py  # 反事实验证记录检查
│   └── skeptic_signoff_checker.py   # Skeptic 五把刀签署验证
└── schemas/
    ├── bugcard_required_fields.yaml # BugCard 必填字段 Schema
    └── skeptic_signoff_schema.yaml  # Skeptic 签署记录 Schema
```

Claude Code 平台的 Hook 触发配置在 `.claude/settings.json`。

---

## 三类 Hook 详细说明

### Hook 1 · BugCard 完整性检查

| 属性 | 值 |
|------|-----|
| 触发时机 | BugCard YAML 写入 `knowledge/library/` 目录后（PostToolUse） |
| 触发工具 | `bugcard_validator.py` |
| 检查项数 | 12 项（字段存在性、格式、长度、签署状态） |
| 失败行为 | 阻止写入，输出缺失字段列表 |

独立运行：
```bash
python3 common/hooks/validators/bugcard_validator.py path/to/bugcard.yaml
python3 common/hooks/validators/bugcard_validator.py path/to/bugcard.yaml --strict
```

### Hook 2 · 反事实验证检查

| 属性 | 值 |
|------|-----|
| 触发时机 | Team Lead 输出 `AIRD_FINAL_VERDICT`（推荐）或「最终裁决/结案」类关键词时（Stop） |
| 触发工具 | `counterfactual_validator.py` |
| 检查项 | evidence 列表中存在 type: counterfactual_test + result: passed + 量化数据 |
| 失败行为 | 阻止结案，要求补充反事实验证 |

独立运行：
```bash
python3 common/hooks/validators/counterfactual_validator.py "$(python3 common/hooks/utils/resolve_session_artifact.py --artifact session_evidence --must-exist)"
```

### Hook 3 · Skeptic 签署检查

| 属性 | 值 |
|------|-----|
| 触发时机 | Team Lead 结案时（Stop）；BugCard 入库时（PostToolUse） |
| 触发工具 | `skeptic_signoff_checker.py` |
| 检查项 | 五把刀全部覆盖 + 全部 pass + sign_off.signed=true + 无 open 质疑 |
| 失败行为 | 阻止继续，列出未解质疑 |

独立运行：
```bash
# 假设签署模式（默认）
python3 common/hooks/validators/skeptic_signoff_checker.py skeptic_output.yaml

# BugCard 签署模式
python3 common/hooks/validators/skeptic_signoff_checker.py skeptic_output.yaml --mode bugcard
```

---

## 平台覆盖策略

| 平台 | Hook 实现方式 | 强制等级 |
|------|-------------|---------|
| **Claude Code** | `.claude/settings.json` 原生 Hooks | 系统级强制（阻断） |
| **Code Buddy** | `platforms/code-buddy/hooks/hooks.json` 原生 Hooks | 系统级强制（阻断） |
| Claude Work | Agent Prompt 内嵌「质量门槛检查」清单 | Prompt 层软约束 |
| Copilot | Agent Prompt 内嵌「质量门槛检查」清单 | Prompt 层软约束 |
| Manus | 工作流 Step 5 和 Step 8 作为显式质量关卡 | 工作流层中等强制 |

---

## 扩展指南：添加新 Hook

1. **写验证脚本** → 放入 `validators/` 目录
   - 遵循退出码规范：0=通过，1=失败，2=解析错误
   - 输出 ANSI 彩色结果（参考现有三个脚本的风格）

2. **写 Schema**（可选）→ 放入 `schemas/` 目录

3. **注册到 Claude Code**：在 `.claude/settings.json` 的 `hooks` 节中添加条目

4. **为其他平台添加 Prompt 层降级**：在对应 Agent 的质量门槛检查清单中新增一行

---

## 依赖

推荐安装方式：
```bash
python3 -m pip install -r common/hooks/requirements.txt
```

或直接安装：
```bash
python3 -m pip install pyyaml
```

验证脚本仅依赖 Python 标准库 + PyYAML，无其他依赖。
