# RenderDoc/RDC GPU Debug · Quality Hooks 系统（质量 Hook）

Quality Hooks 系统将 Debugger 框架的质量门槛从“被建议的”提升为“被强制执行的”。

补充说明：

- 对拥有 native hooks 的宿主，Hook 只负责触发共享 harness，不承载平台私有业务规则。
- 对 pseudo-hooks / no-hooks 宿主，最终仍以 `workspace/cases/<case_id>/runs/<run_id>/artifacts/run_compliance.yaml` 为统一审计裁决。
- 审计现在同时校验 `case_input.yaml`、`fix_verification.yaml`、`session_evidence.yaml` 与 versioned spec snapshot 的绑定关系。
- 共享流程入口统一由 `utils/harness_guard.py` 提供：`preflight`、`accept-intake`、`dispatch-readiness`、`dispatch-specialist`、`specialist-feedback`、`final-audit`、`render-user-verdict`。

## 架构

```text
common/hooks/
├── README.md
├── schemas/
│   ├── hypothesis_board_schema.yaml
│   └── ...
├── validators/
│   ├── bugcard_validator.py
│   ├── hypothesis_board_validator.py
│   ├── intake_validator.py
│   ├── counterfactual_validator.py
│   └── skeptic_signoff_checker.py
├── utils/
│   ├── harness_guard.py
│   ├── spec_store.py
│   ├── knowledge_evolution.py
│   ├── run_compliance_audit.py
│   └── validate_tool_contract_runtime.py
└── schemas/
    ├── bugcard_required_fields.yaml
    ├── fix_verification_schema.yaml
    ├── intake_case_input_schema.yaml
    ├── skeptic_signoff_schema.yaml
    └── run_compliance_schema.yaml
```

## 审计边界

`run_compliance.yaml` 现在只承担派生审计职责，并额外输出 run 级 metrics：

- per-agent 耗时与事件数
- tool success / failure 与失败率
- hypothesis 状态分布
- conflict 总数、仲裁数、平均仲裁时延
- counterfactual 独立复核覆盖率
- knowledge candidate 发射与状态迁移数

这些指标与 gate 结论从 `case_input.yaml`、`fix_verification.yaml`、`action_chain.jsonl`、`session_evidence.yaml`、`registry/active_manifest.yaml` 派生，不从 prose report 反推。

## 新的知识演化约束

- `intake_validator.py` 负责保证 `case_input.yaml` 满足单一 intake 合同。
- `hypothesis_board_validator.py` 负责保证 `hypothesis_board.yaml` 既满足 orchestration 控制需求，也满足用户面板状态源需求。
- `bugcard_validator.py` 的 strict 模式只认 active manifest 当前指向的 taxonomy / invariant / SOP。
- `run_compliance_audit.py` 会在合规 run 上自动发射 candidate，并把事件写入 `evolution_ledger.jsonl`。
- 自动晋升、自动回滚与 negative memory 由 `knowledge_evolution.py` 管理；不得绕过它直接改 manifest。

## 依赖

推荐安装方式：

```bash
python3 -m pip install -r common/hooks/requirements.txt
```

验证脚本仅依赖 Python 标准库 + PyYAML。
