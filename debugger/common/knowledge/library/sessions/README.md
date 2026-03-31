# Session Artifacts（会话产物）

当前目录用于存放 live per-session 的必需 artifacts。

必需路径：
- `<session_id>/session_evidence.yaml`
- `<session_id>/skeptic_signoff.yaml`
- `<session_id>/action_chain.jsonl`
- `.current_session`（plain text；记录当前 `session_id`）

不要在本目录存放 examples。示例 session 应放在 `../../examples/sessions/`。

在 finalization 之前，必须先更新 `.current_session`。

`session_evidence.yaml` 的 root object 必须包含：
- `causal_anchor.type`
- `causal_anchor.ref`
- `causal_anchor.established_by`
- `causal_anchor.justification`

当前允许的 evidence item type 包含 `causal_anchor_evidence` 与 `visual_fallback_observation`。
`visual_fallback_observation` 可用于 selection 和 sanity check，但不能替代 `causal_anchor_evidence`。
