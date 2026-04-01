# 知识演化指南

本文档说明 Debugger framework 如何从合规 run 自动生成 candidate、完成 replay / shadow 验证，并在达标后自动切换 active spec。

## 固定流程

```text
compliant run
    │
    ▼
action_chain.jsonl + session_evidence.yaml + approved counterfactual reviews
    │
    ▼
candidate emission / dedupe
    │
    ▼
replay validation
    │
    ▼
shadow observation
    │
    ▼
active / rolled_back / rejected / manual_hold
```

## 输入来源

- `action_chain.jsonl`
- `session_evidence.yaml`
- BugCard / BugFull
- counterfactual approved reviews

## 合规前提

只有满足以下条件的 run 才能进入知识演化：

- 未绕过 `BLOCKED_MISSING_FIX_REFERENCE`
- challenge / redispatch 已完整关闭
- `run_compliance.yaml` 无 unresolved `process_deviation`

## 新 run 召回原则

- 新 run 只能召回历史结构化真相
- reopen / reconnect 产生新的 `session_id` 是正常行为
- 历史 run 不复用 live handle，也不维护第二套 session continuity 镜像
