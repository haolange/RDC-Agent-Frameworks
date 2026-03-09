# Session Artifacts

This directory stores live per-session mandatory artifacts.

Required paths:
- `<session_id>/session_evidence.yaml`
- `<session_id>/skeptic_signoff.yaml`
- `<session_id>/action_chain.jsonl`
- `.current_session` (plain text; current session id)

Do not store examples in this directory. Example sessions live under `../../examples/sessions/`.

Update `.current_session` before finalization.

`session_evidence.yaml` root object must include:
- `causal_anchor.type`
- `causal_anchor.ref`
- `causal_anchor.established_by`
- `causal_anchor.justification`

Allowed evidence item types now include `causal_anchor_evidence` and `visual_fallback_observation`.
`visual_fallback_observation` may be used for selection and sanity checks, but it cannot replace `causal_anchor_evidence`.

