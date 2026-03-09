# Cursor Platform Quality Hooks

Cursor平台的RenderDoc/RDC GPU Debug框架质量门槛Hooks系统。

## 概述

由于Cursor IDE没有像Claude Code那样的原生hooks系统，本实现提供了一套适配层，通过以下方式实现质量门槛检查：

1. **hooks.json** - 定义了PostToolUse和Stop事件的hooks配置
2. **验证脚本** - 包装了common/hooks中的验证器
3. **工具脚本** - 提供Cursor特定的hook分发和审计功能
4. **Schema定义** - Cursor平台特定的验证schema

## 目录结构

```
hooks/
├── hooks.json                          # Hooks配置文件
├── README.md                           # 本文件
├── validators/                         # 验证脚本
│   ├── bugcard_validator.py           # BugCard完整性检查
│   ├── counterfactual_validator.py    # 反事实验证检查
│   ├── skeptic_signoff_checker.py     # Skeptic签署验证
│   └── causal_anchor_validator.py     # 因果锚点验证
├── utils/                              # 工具脚本
│   ├── cursor_hook_dispatch.py        # Hook分发器
│   ├── run_compliance_audit.py        # 运行合规审计
│   ├── validate_tool_contract_runtime.py  # 工具契约验证
│   └── resolve_session_artifact.py    # Session产物解析
└── schemas/                            # Schema定义
    ├── bugcard_required_fields.yaml   # BugCard必填字段
    ├── skeptic_signoff_schema.yaml    # Skeptic签署格式
    └── run_compliance_schema.yaml     # 运行合规Schema
```

## 使用方式

### 1. 环境变量配置

在Cursor IDE或系统环境中设置以下变量：

```bash
export DEBUGGER_ROOT="/path/to/debugger"  # Debugger框架根目录
export CURSOR_WRITE_PATH=""               # 当前写入的文件路径（由IDE设置）
export CURSOR_SESSION_ID=""               # 当前会话ID（可选）
```

### 2. 在.cursorrules中配置

在项目的`.cursorrules`文件中添加规则：

```markdown
## Quality Gates

### BugCard Write Validation
- 在写入 `knowledge/library/bugcards/*.yaml` 前，运行：
  ```bash
  python ${DEBUGGER_ROOT}/platforms/cursor/hooks/validators/bugcard_validator.py <file>
  ```

### Finalization Gate
- 在输出 `DEBUGGER_FINAL_VERDICT` 或结案前，运行：
  ```bash
  python ${DEBUGGER_ROOT}/platforms/cursor/hooks/utils/cursor_hook_dispatch.py stop-gate
  ```

### Skeptic Signoff Validation
- 在写入 `knowledge/library/sessions/*/skeptic_signoff.yaml` 前，运行：
  ```bash
  python ${DEBUGGER_ROOT}/platforms/cursor/hooks/validators/skeptic_signoff_checker.py <file> --mode bugcard
  ```
```

### 3. 手动运行验证

```bash
# BugCard验证
python validators/bugcard_validator.py path/to/bugcard.yaml [--strict]

# Skeptic签署验证
python validators/skeptic_signoff_checker.py path/to/skeptic_signoff.yaml [--mode {format|bugcard|hypothesis}]

# 反事实验证
python validators/counterfactual_validator.py path/to/session_evidence.yaml

# 因果锚点验证
python validators/causal_anchor_validator.py path/to/session_evidence.yaml

# 最终结案gate检查
python utils/cursor_hook_dispatch.py stop-gate

# 运行合规审计
python utils/run_compliance_audit.py [--strict]
```

## Hooks配置详解

### PostToolUse事件

1. **BugCard写入验证**
   - 触发条件：写入 `**/knowledge/library/**/*bugcard*.yaml`
   - 验证内容：12项必填字段、schema格式、引用一致性
   - 失败行为：阻止写入

2. **Skeptic签署验证**
   - 触发条件：写入 `**/knowledge/library/sessions/**/skeptic_signoff.yaml`
   - 验证内容：五把刀覆盖、签署状态
   - 失败行为：警告（不阻止）

### Stop事件

**最终结案Gate检查**
- 触发条件：输出包含 `DEBUGGER_FINAL_VERDICT|最终裁决|根因确认|结案|final verdict|case closed`
- 验证内容：
  - 工具契约验证
  - Session证据产物存在性
  - Skeptic签署产物存在性
  - Action Chain产物存在性
  - 因果锚点验证
  - 反事实验证
  - Skeptic签署验证
  - 运行合规审计
- 失败行为：阻止结案

## 验证流程

```
┌─────────────────────────────────────────────────────────────┐
│                     PostToolUse Hooks                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  BugCard Write                                              │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ Tool Contract│ -> │ BugCard     │ -> │ Skeptic     │     │
│  │ Validation   │    │ Schema      │    │ Signoff     │     │
│  │              │    │ Validation  │    │ Check       │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│       │                    │                  │             │
│       ▼                    ▼                  ▼             │
│  [Pass] -> 允许写入    [Pass] -> 继续    [Pass] -> 完成      │
│  [Fail] -> 阻止写入    [Fail] -> 阻止    [Fail] -> 警告      │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       Stop Hooks                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Finalization Trigger (DEBUGGER_FINAL_VERDICT)              │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Finalization Gate                  │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  1. Tool Contract Validation                        │   │
│  │  2. Session Evidence Exists                         │   │
│  │  3. Skeptic Signoff Exists                          │   │
│  │  4. Action Chain Exists                             │   │
│  │  5. Causal Anchor Validation                        │   │
│  │  6. Counterfactual Validation                       │   │
│  │  7. Skeptic Signoff Validation                      │   │
│  │  8. Run Compliance Audit                            │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                     │
│       ▼                                                     │
│  [All Pass] -> 允许结案                                     │
│  [Any Fail] -> 阻止结案，输出缺失项                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 与Common Hooks的关系

本目录下的验证脚本都是`common/hooks`中对应脚本的包装器，提供：

1. **路径解析** - 自动解析DEBUGGER_ROOT环境变量
2. **输出格式化** - 添加`[cursor-*]`前缀便于识别
3. **错误处理** - Cursor特定的错误提示

实际验证逻辑位于：
- `common/hooks/validators/` - 通用验证器
- `common/hooks/utils/` - 通用工具
- `common/hooks/schemas/` - 通用Schema

## 退出码规范

所有验证脚本遵循以下退出码规范：

| 退出码 | 含义 |
|--------|------|
| 0 | 验证通过 |
| 1 | 验证失败（有具体错误信息） |
| 2 | 文件/依赖错误（脚本或依赖缺失） |
| 3 | 产物不存在（仅resolve_session_artifact） |

## 依赖

- Python 3.8+
- PyYAML (`pip install pyyaml`)

## 注意事项

1. **Cursor限制** - Cursor没有像Claude Code那样的原生hook系统，需要通过`.cursorrules`或手动运行
2. **环境变量** - 确保`DEBUGGER_ROOT`环境变量正确设置
3. **Session标记** - 某些验证需要`common/knowledge/library/sessions/.current_session`文件
4. **审计产物** - 最终合规性以`workspace/cases/<case_id>/runs/<run_id>/artifacts/run_compliance.yaml`为准
