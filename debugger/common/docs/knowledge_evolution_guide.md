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
- cross-device fingerprint graph

## Candidate 触发条件

满足以下任一条件即可自动发起 candidate：

- 当前 run 没有匹配到 active SOP
- 命中的 SOP 遵循度低于阈值
- 当前 symptom / trigger / invariant 组合无法被 active spec 精确覆盖
- 现有 invariant 无法完整解释结论
- taxonomy 出现 `unclassified` 或高混淆标签信号

## Candidate 状态机

- `candidate`
- `replay_validated`
- `shadow_active`
- `active`
- `rolled_back`
- `rejected`
- `manual_hold`

## 自动晋升

- candidate 先满足 family 对应的 replay 阈值
- 再满足 shadow 阶段的连续无 critical regression 条件
- 达标后只切换 `registry/active_manifest.yaml` 与 `spec_registry.yaml`
- 旧版本不删除，只作为 rollback target 保留

## 自动回滚

出现以下任一条件时自动回滚：

- 连续 critical regression 达阈值
- false route rate delta 超阈值
- counterfactual approved rate 低于下限

回滚后必须：

- 写入 `spec/ledger/evolution_ledger.jsonl`
- 记录到 `spec/negative_memory.yaml`
- 阻止同类坏候选在短窗口内重复晋升
