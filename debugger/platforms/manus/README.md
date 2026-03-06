# Manus Adaptation

这是面向 `Manus` 的 workflow-level 降级适配。

## 提供内容

- `workflows/00_debug_workflow.md`
- `references/entrypoints.md`

## 明确边界

- 不宣称 custom agents
- 不宣称 hooks
- 不宣称 skills
- 不宣称 per-agent model routing

## Artifact 要求

即使作为 workflow 宿主，也必须遵守：

- `session_evidence.yaml`
- `skeptic_signoff.yaml`
- `action_chain.jsonl`
- `.current_session`

缺失这些产物时，不得视为有效结案。
