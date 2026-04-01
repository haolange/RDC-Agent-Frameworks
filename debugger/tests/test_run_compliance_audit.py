from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(f"PyYAML is required for tests: {exc}")


REPO_ROOT = Path(__file__).resolve().parents[2]
DEBUGGER_ROOT = REPO_ROOT / "debugger"
AUDIT_SCRIPT = DEBUGGER_ROOT / "common" / "hooks" / "utils" / "run_compliance_audit.py"
ENTRY_GATE_SCRIPT = DEBUGGER_ROOT / "common" / "hooks" / "utils" / "entry_gate.py"
INTAKE_GATE_SCRIPT = DEBUGGER_ROOT / "common" / "hooks" / "utils" / "intake_gate.py"
TOPOLOGY_SCRIPT = DEBUGGER_ROOT / "common" / "hooks" / "utils" / "runtime_topology.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_module(path: Path, module_name: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _seed_base(root: Path) -> None:
    for rel in (
        Path("common/config/framework_compliance.json"),
        Path("common/config/platform_capabilities.json"),
        Path("common/config/runtime_mode_truth.snapshot.json"),
        Path("common/knowledge/spec/README.md"),
        Path("common/knowledge/spec/registry/active_manifest.yaml"),
        Path("common/knowledge/spec/registry/spec_registry.yaml"),
        Path("common/knowledge/spec/policy/evolution_policy.yaml"),
        Path("common/knowledge/spec/negative_memory.yaml"),
        Path("common/knowledge/spec/ledger/evolution_ledger.jsonl"),
        Path("common/knowledge/spec/objects/sops/SOP-CATALOG@1.yaml"),
        Path("common/knowledge/spec/objects/sops/SOP-CATALOG@1.payload.yaml"),
        Path("common/knowledge/spec/objects/invariants/INVARIANT-CATALOG@1.yaml"),
        Path("common/knowledge/spec/objects/invariants/INVARIANT-CATALOG@1.payload.yaml"),
        Path("common/knowledge/spec/objects/taxonomy/SYMPTOM-TAXONOMY@1.yaml"),
        Path("common/knowledge/spec/objects/taxonomy/SYMPTOM-TAXONOMY@1.payload.yaml"),
        Path("common/knowledge/spec/objects/taxonomy/TRIGGER-TAXONOMY@1.yaml"),
        Path("common/knowledge/spec/objects/taxonomy/TRIGGER-TAXONOMY@1.payload.yaml"),
    ):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DEBUGGER_ROOT / rel, target)


def _rt_payload(
    *,
    entry_mode: str = "cli",
    backend: str = "local",
    context_id: str = "ctx-default",
    runtime_owner: str = "rdc-debugger",
    baton_ref: str = "",
    context_binding_id: str | None = None,
    capture_ref: str = "capture:anomalous",
    canonical_anchor_ref: str = "event:523",
    **extra: object,
) -> dict[str, object]:
    binding_id = context_binding_id or f"ctxbind-{context_id}"
    return {
        "entry_mode": entry_mode,
        "backend": backend,
        "context_id": context_id,
        "runtime_owner": runtime_owner,
        "baton_ref": baton_ref,
        "context_binding_id": binding_id,
        "capture_ref": capture_ref,
        "canonical_anchor_ref": canonical_anchor_ref,
        **extra,
    }


def _base_action_chain(session_id: str, run_id: str, *, case_id: str = "case_001", reviewer: str = "skeptic_agent") -> list[dict]:
    return [
        {
            "schema_version": "2",
            "event_id": "evt-0001-intake-gate",
            "ts_ms": 1772537599900,
            "run_id": run_id,
            "session_id": session_id,
            "agent_id": "rdc-debugger",
            "event_type": "quality_check",
            "status": "pass",
            "duration_ms": 0,
            "refs": [],
            "payload": _rt_payload(validator="intake_gate", summary="run intake gate passed"),
        },
        {
            "schema_version": "2",
            "event_id": "evt-0002-dispatch",
            "ts_ms": 1772537600000,
            "run_id": run_id,
            "session_id": session_id,
            "agent_id": "rdc-debugger",
            "event_type": "dispatch",
            "status": "sent",
            "duration_ms": 15,
            "refs": [],
            "payload": _rt_payload(
                context_id="ctx-orchestrator",
                runtime_owner="rdc-debugger",
                target_agent="pixel_forensics_agent",
                objective="inspect the anomalous hotspot",
            ),
        },
        {
            "schema_version": "2",
            "event_id": "evt-0003-tool",
            "ts_ms": 1772537600500,
            "run_id": run_id,
            "session_id": session_id,
            "agent_id": "pixel_forensics_agent",
            "event_type": "tool_execution",
            "status": "ok",
            "duration_ms": 120,
            "refs": ["evt-0002-dispatch"],
            "payload": _rt_payload(
                context_id="ctx-pixel",
                runtime_owner="pixel_forensics_agent",
                tool_name="rd.debug.pixel_history",
                transport="daemon",
            ),
        },
        {
            "schema_version": "2",
            "event_id": "evt-0004-specialist-artifact",
            "ts_ms": 1772537600750,
            "run_id": run_id,
            "session_id": session_id,
            "agent_id": "pixel_forensics_agent",
            "event_type": "artifact_write",
            "status": "written",
            "duration_ms": 12,
            "refs": ["evt-0003-tool"],
            "payload": _rt_payload(
                context_id="ctx-pixel",
                runtime_owner="pixel_forensics_agent",
                path=f"workspace/cases/{case_id}/runs/{run_id}/notes/pixel_forensics.md",
                artifact_role="specialist_handoff",
            ),
        },
        {
            "schema_version": "2",
            "event_id": "evt-0005-hypothesis",
            "ts_ms": 1772537600900,
            "run_id": run_id,
            "session_id": session_id,
            "agent_id": "rdc-debugger",
            "event_type": "hypothesis_transition",
            "status": "applied",
            "duration_ms": 20,
            "refs": ["evt-0003-tool"],
            "payload": {
                "hypothesis_id": "H-001",
                "from_state": "OPEN",
                "to_state": "ACTIVE",
                "reason": "anchor established",
            },
        },
        {
            "schema_version": "2",
            "event_id": "evt-0006-conflict-open",
            "ts_ms": 1772537601200,
            "run_id": run_id,
            "session_id": session_id,
            "agent_id": "driver_device_agent",
            "event_type": "conflict_opened",
            "status": "open",
            "duration_ms": 18,
            "refs": ["H-001"],
            "payload": {
                "conflict_id": "CONFLICT-001",
                "hypothesis_id": "H-001",
                "positions": [
                    {"agent_id": "shader_ir_agent", "stance": "support", "evidence_refs": ["evt-0003-tool"]},
                    {"agent_id": "driver_device_agent", "stance": "refute", "evidence_refs": ["evt-0005-hypothesis"]},
                ],
            },
        },
        {
            "schema_version": "2",
            "event_id": "evt-0007-conflict-resolved",
            "ts_ms": 1772537601500,
            "run_id": run_id,
            "session_id": session_id,
            "agent_id": "skeptic_agent",
            "event_type": "conflict_resolved",
            "status": "resolved",
            "duration_ms": 50,
            "refs": ["CONFLICT-001", "H-001"],
            "payload": {
                "conflict_id": "CONFLICT-001",
                "hypothesis_id": "H-001",
                "reviewer_agent": "skeptic_agent",
                "decision": "support_precision_hypothesis",
                "rationale": "structured evidence aligns",
            },
        },
        {
            "schema_version": "2",
            "event_id": "evt-0008-counterfactual-submit",
            "ts_ms": 1772537602200,
            "run_id": run_id,
            "session_id": session_id,
            "agent_id": "shader_ir_agent",
            "event_type": "counterfactual_submitted",
            "status": "submitted",
            "duration_ms": 140,
            "refs": ["evt-0003-tool", "H-001"],
            "payload": {
                "review_id": "CF-001",
                "hypothesis_id": "H-001",
                "proposer_agent": "shader_ir_agent",
                "intervention": "half diffuse -> float diffuse",
                "target_variable": "shader precision",
                "reference_contract_ref": f"../workspace/cases/{case_id}/case_input.yaml#reference_contract",
                "verification_mode": "device_parity",
                "baseline_source": {"kind": "capture_baseline", "ref": "capture:baseline"},
                "probe_results": [
                    {
                        "probe_id": "hair_hotspot",
                        "probe_type": "pixel",
                        "pixel_before": {"x": 512, "y": 384, "rgba": [0.21, 0.19, 0.18, 1.0]},
                        "pixel_after": {"x": 512, "y": 384, "rgba": [0.37, 0.34, 0.32, 1.0]},
                        "pixel_baseline": {"x": 512, "y": 384, "rgba": [0.38, 0.35, 0.33, 1.0]},
                    }
                ],
                "isolation_checks": {
                    "only_target_changed": True,
                    "same_scene_same_input": True,
                    "same_drawcall_count": True,
                },
                "measurements": {
                    "pixel_before": {"x": 512, "y": 384, "rgba": [0.21, 0.19, 0.18, 1.0]},
                    "pixel_after": {"x": 512, "y": 384, "rgba": [0.37, 0.34, 0.32, 1.0]},
                    "pixel_baseline": {"x": 512, "y": 384, "rgba": [0.38, 0.35, 0.33, 1.0]},
                },
                "scoring": {
                    "pixel_recovery": 0.94,
                    "variable_isolation": 1.0,
                    "symptom_coverage": 1.0,
                    "total": 0.97,
                },
                "evidence_refs": ["evt-0003-tool", "evt-0007-conflict-resolved"],
            },
        },
        {
            "schema_version": "2",
            "event_id": "evt-0009-counterfactual-review",
            "ts_ms": 1772537602500,
            "run_id": run_id,
            "session_id": session_id,
            "agent_id": reviewer,
            "event_type": "counterfactual_reviewed",
            "status": "approved",
            "duration_ms": 60,
            "refs": ["CF-001", "evt-0008-counterfactual-submit"],
            "payload": {
                "review_id": "CF-001",
                "hypothesis_id": "H-001",
                "reviewer_agent": reviewer,
                "semantic_verdict": "strict_pass",
                "isolation_verdict": {"verdict": "isolated", "rationale": "all isolation checks passed"},
                "evidence_refs": ["evt-0008-counterfactual-submit", "evt-0003-tool"],
            },
        },
        {
            "schema_version": "2",
            "event_id": "evt-0010-artifact",
            "ts_ms": 1772537602800,
            "run_id": run_id,
            "session_id": session_id,
            "agent_id": "curator_agent",
            "event_type": "artifact_write",
            "status": "written",
            "duration_ms": 10,
            "refs": ["evt-0009-counterfactual-review"],
            "payload": _rt_payload(
                context_id="ctx-curator",
                runtime_owner="curator_agent",
                path=f"workspace/cases/{case_id}/runs/{run_id}/reports/report.md",
                artifact_role="workspace_report",
            ),
        },
    ]


def _seed_common_session(
    root: Path,
    session_id: str,
    run_id: str,
    *,
    case_id: str = "case_001",
    reviewer: str = "skeptic_agent",
    conflict_status: str = "ARBITRATED",
    hypothesis_status: str = "VALIDATED",
    review_event_id: str = "evt-0009-counterfactual-review",
) -> None:
    sessions_root = root / "common" / "knowledge" / "library" / "sessions"
    sessions_root.mkdir(parents=True, exist_ok=True)
    _write(sessions_root / ".current_session", f"{session_id}\n")

    action_chain = _base_action_chain(session_id, run_id, case_id=case_id, reviewer=reviewer)
    _write(
        sessions_root / session_id / "action_chain.jsonl",
        "\n".join(json.dumps(event, ensure_ascii=False) for event in action_chain) + "\n",
    )

    snapshot = {
        "schema_version": "2",
        "session_id": session_id,
        "snapshot_version": 1,
        "spec_snapshot_ref": "spec-snapshot-20260315-0001",
        "active_spec_versions": {
            "sop_catalog": 1,
            "invariant_catalog": 1,
            "symptom_taxonomy": 1,
            "trigger_taxonomy": 1,
        },
        "causal_anchor": {
            "type": "root_drawcall",
            "ref": "event:523",
            "established_by": "pixel_forensics_agent",
            "justification": "fixture anchor",
            "evidence_refs": ["evt-0003-tool"],
        },
        "reference_contract": {
            "ref": f"../workspace/cases/{case_id}/case_input.yaml#reference_contract",
            "source_kind": "capture_baseline",
            "verification_mode": "device_parity",
            "fallback_only": False,
        },
        "fix_verification": {
            "ref": f"../workspace/cases/{case_id}/runs/{run_id}/artifacts/fix_verification.yaml",
            "structural_status": "passed",
            "semantic_status": "passed",
            "overall_status": "passed",
        },
        "hypotheses": [
            {
                "hypothesis_id": "H-001",
                "status": hypothesis_status,
                "title": "precision regression",
                "lead_agent": "shader_ir_agent",
                "evidence_refs": ["evt-0003-tool", "evt-0009-counterfactual-review"],
                "conflict_ids": ["CONFLICT-001"],
            }
        ],
        "conflicts": [
            {
                "conflict_id": "CONFLICT-001",
                "hypothesis_id": "H-001",
                "status": conflict_status,
                "opened_at_ms": 1772537601200,
                "resolved_at_ms": 1772537601500,
                "opened_by_event": "evt-0006-conflict-open",
                "resolved_by_event": "evt-0007-conflict-resolved",
                "positions": [
                    {"agent_id": "shader_ir_agent", "stance": "support", "evidence_refs": ["evt-0003-tool"]},
                    {"agent_id": "driver_device_agent", "stance": "refute", "evidence_refs": ["evt-0005-hypothesis"]},
                ],
                "arbitration": {
                    "reviewer_agent": "skeptic_agent",
                    "decision": "support_precision_hypothesis",
                    "rationale": "fixture arbitration",
                },
            }
        ],
        "counterfactual_reviews": [
            {
                "review_id": "CF-001",
                "hypothesis_id": "H-001",
                "proposer_agent": "shader_ir_agent",
                "reviewer_agent": reviewer,
                "status": "approved",
                "submission_event_id": "evt-0008-counterfactual-submit",
                "review_event_id": review_event_id,
                "evidence_refs": ["evt-0003-tool", "evt-0008-counterfactual-submit"],
            }
        ],
        "knowledge_candidates": [],
        "evidence_refs": ["evt-0003-tool", "evt-0007-conflict-resolved", "evt-0009-counterfactual-review"],
        "store_contract": {
            "ledger_artifact": "action_chain.jsonl",
            "snapshot_artifact": "session_evidence.yaml",
            "active_spec_snapshot_artifact": "common/knowledge/spec/registry/active_manifest.yaml",
            "governance_ledger_artifact": "common/knowledge/spec/ledger/evolution_ledger.jsonl",
            "derived_artifacts": ["run_compliance.yaml"],
            "truth_roles": {
                "action_chain": "append_only_ledger",
                "session_evidence": "adjudicated_snapshot",
                "active_spec_snapshot": "versioned_spec_pointer",
                "evolution_ledger": "append_only_governance_ledger",
                "run_compliance": "derived_audit",
            },
        },
    }
    _write(sessions_root / session_id / "session_evidence.yaml", yaml.safe_dump(snapshot, sort_keys=False, allow_unicode=True))

    signoff = [
        {
            "message_type": "SKEPTIC_SIGN_OFF",
            "from": "skeptic_agent",
            "to": "rdc-debugger",
            "target_hypothesis": "H-001",
            "blade_review": [
                {"blade": "刀1: 相关性刀", "result": "pass", "note": "ok"},
                {"blade": "刀2: 覆盖性刀", "result": "pass", "note": "ok"},
                {"blade": "刀3: 反事实刀", "result": "pass", "note": "ok"},
                {"blade": "刀4: 工具证据刀", "result": "pass", "note": "ok"},
                {"blade": "刀5: 替代假设刀", "result": "pass", "note": "ok"},
                {"blade": "刀6: 语义基准刀", "result": "pass", "note": "ok"},
            ],
            "sign_off": {"signed": True, "declaration": "evidence chain is sufficient"},
        }
    ]
    _write(sessions_root / session_id / "skeptic_signoff.yaml", yaml.safe_dump(signoff, sort_keys=False, allow_unicode=True))


def _seed_intake_gate(root: Path, run_root: Path) -> None:
    module = _load_module(INTAKE_GATE_SCRIPT, f"intake_gate_module_{run_root.name}")
    module.run_intake_gate(root, run_root)


def _seed_entry_gate(
    root: Path,
    run_root: Path,
    *,
    platform: str,
    entry_mode: str = "cli",
    backend: str = "local",
    single_agent_by_user: bool = False,
) -> None:
    module = _load_module(ENTRY_GATE_SCRIPT, f"entry_gate_module_{run_root.name}_{platform}")
    case_root = run_root.parent.parent
    capture_paths = [
        str((case_root / "inputs" / "captures" / "broken.rdc").resolve()),
        str((case_root / "inputs" / "captures" / "good.rdc").resolve()),
    ]
    module.run_entry_gate(
        root,
        case_root,
        platform=platform,
        entry_mode=entry_mode,
        backend=backend,
        capture_paths=capture_paths,
        mcp_configured=entry_mode == "mcp",
        remote_transport="adb_android" if backend == "remote" else "",
        single_agent_requested=single_agent_by_user,
    )


def _seed_runtime_topology(root: Path, run_root: Path, *, platform: str) -> None:
    module = _load_module(TOPOLOGY_SCRIPT, f"runtime_topology_module_{run_root.name}_{platform}")
    module.run_runtime_topology(root, run_root, platform=platform)


def _seed_remote_artifacts(
    run_root: Path,
    *,
    blocked_capability_codes: list[str] | None = None,
    reconnect_required: bool = False,
    inconsistency_status: str = "clear",
) -> None:
    blocked_codes = [str(item).strip() for item in (blocked_capability_codes or []) if str(item).strip()]
    _write(
        run_root / "artifacts" / "remote_prerequisite_gate.yaml",
        yaml.safe_dump(
            {
                "status": "passed",
                "blocking_codes": [],
                "remote_transport": "adb_android",
            },
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    _write(
        run_root / "artifacts" / "remote_capability_gate.yaml",
        yaml.safe_dump(
            {
                "status": "blocked" if blocked_codes else "passed",
                "blocked_capability_codes": blocked_codes,
                "remote_capability_matrix": {
                    "endpoint": {"status": "ready"},
                    "replay": {"status": "ready"},
                    "event_bound_inspection": {"status": "ready"},
                    "shader_debug": {"status": "blocked" if blocked_codes else "ready", "blocking_codes": blocked_codes},
                    "shader_replace": {"status": "blocked" if blocked_codes else "ready", "blocking_codes": blocked_codes},
                    "shader_compile": {"status": "ready"},
                    "fix_verification": {"status": "blocked" if blocked_codes else "ready", "blocking_codes": blocked_codes},
                },
            },
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    _write(
        run_root / "artifacts" / "remote_recovery_decision.yaml",
        yaml.safe_dump(
            {
                "status": "blocked" if reconnect_required else "passed",
                "reconnect_required": reconnect_required,
                "blocking_codes": ["BLOCKED_REMOTE_SESSION_REOPEN_REQUIRED"] if reconnect_required else [],
                "decision": "reconnect_required" if reconnect_required else "reuse_current_context",
            },
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    _write(
        run_root / "notes" / "remote_planning_brief.yaml",
        yaml.safe_dump(
            {
                "status": "ready",
                "summary": "remote plan recorded",
            },
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    _write(
        run_root / "notes" / "remote_runtime_inconsistency.yaml",
        yaml.safe_dump(
            {
                "status": inconsistency_status,
                "summary": "no inconsistency detected" if inconsistency_status == "clear" else "remote inconsistency captured",
                "blocking_codes": [],
            },
            sort_keys=False,
            allow_unicode=True,
        ),
    )


def _seed_run(
    root: Path,
    case_id: str,
    run_id: str,
    platform: str,
    coordination_mode: str,
    *,
    knowledge_context: dict | None = None,
    intent_gate_override: dict | None = None,
    single_agent_by_user: bool = False,
) -> Path:
    case_root = root / "workspace" / "cases" / case_id
    run_root = case_root / "runs" / run_id
    entry_mode = "cli"
    _write(case_root / "case.yaml", f"case_id: {case_id}\ncurrent_run: {run_id}\nreference_contract_ref: ../workspace/cases/{case_id}/case_input.yaml#reference_contract\n")
    case_input = {
        "schema_version": "1",
        "case_id": case_id,
        "session": {"mode": "cross_device", "goal": "validate fixture"},
        "symptom": {"summary": "fixture summary"},
        "captures": [
            {
                "capture_id": "cap-anomalous-001",
                "role": "anomalous",
                "file_name": "broken.rdc",
                "source": "user_supplied",
                "provenance": {"device": "fixture-a"},
            },
            {
                "capture_id": "cap-baseline-001",
                "role": "baseline",
                "file_name": "good.rdc",
                "source": "historical_good",
                "provenance": {"build": "1487"},
            },
        ],
        "environment": {"api": "Vulkan"},
        "reference_contract": {
            "source_kind": "capture_baseline",
            "source_refs": ["capture:baseline"],
            "verification_mode": "device_parity",
            "probe_set": {"pixels": [{"name": "hair_hotspot", "x": 512, "y": 384}]},
            "acceptance": {"max_channel_delta": 0.05, "fallback_only": False},
        },
        "hints": {},
        "project": {"engine": "fixture"},
    }
    _write(case_root / "case_input.yaml", yaml.safe_dump(case_input, sort_keys=False, allow_unicode=True))
    _write(
        case_root / "inputs" / "captures" / "manifest.yaml",
        yaml.safe_dump(
            {
                "captures": [
                    {
                        "capture_id": "cap-anomalous-001",
                        "capture_role": "anomalous",
                        "file_name": "broken.rdc",
                        "source": "user_supplied",
                        "import_mode": "path",
                        "imported_at": "2026-03-24T00:00:00Z",
                        "sha256": "sha-broken",
                        "source_path": "C:/captures/broken.rdc",
                    },
                    {
                        "capture_id": "cap-baseline-001",
                        "capture_role": "baseline",
                        "file_name": "good.rdc",
                        "source": "historical_good",
                        "import_mode": "path",
                        "imported_at": "2026-03-24T00:00:00Z",
                        "sha256": "sha-good",
                        "source_path": "C:/captures/good.rdc",
                    },
                ]
            },
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    _write(case_root / "inputs" / "captures" / "broken.rdc", "broken-capture")
    _write(case_root / "inputs" / "captures" / "good.rdc", "good-capture")
    _write(
        case_root / "inputs" / "references" / "manifest.yaml",
        yaml.safe_dump({"references": [{"reference_id": "golden-001", "file_name": "golden.png", "source_kind": "external_image"}]}, sort_keys=False, allow_unicode=True),
    )
    run_payload = {
        "case_id": case_id,
        "run_id": run_id,
        "platform": platform,
        "coordination_mode": coordination_mode,
        "session_id": "sess_fixture_001",
        "capture_file_id": "capf_fixture_001",
        "runtime": {
            "entry_mode": entry_mode,
            "backend": "local",
            "context_id": "ctx-orchestrator",
            "runtime_owner": "rdc-debugger",
            "coordination_mode": coordination_mode,
            "orchestration_mode": "single_agent_by_user" if single_agent_by_user else "multi_agent",
            "single_agent_reason": "user_requested" if single_agent_by_user else "",
        },
    }
    if knowledge_context is not None:
        run_payload["knowledge_context"] = knowledge_context
    _write(run_root / "run.yaml", yaml.safe_dump(run_payload, sort_keys=False, allow_unicode=True))
    _write(
        run_root / "capture_refs.yaml",
        yaml.safe_dump(
            {
                "captures": [
                    {"capture_id": "cap-anomalous-001", "capture_role": "anomalous", "file_name": "broken.rdc"},
                    {"capture_id": "cap-baseline-001", "capture_role": "baseline", "file_name": "good.rdc"},
                ]
            },
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    _write(
        run_root / "artifacts" / "fix_verification.yaml",
        yaml.safe_dump(
            {
                "schema_version": "1",
                "verdict": "root_cause_validated_fix_verified",
                "verification_mode": "strict",
                "verification_confidence": "high",
                "blocked_by_capability": False,
                "blocked_capability_codes": [],
                "candidate_fix_prepared": True,
                "candidate_fix_live_applied": True,
                "candidate_fix_structurally_validated": True,
                "candidate_fix_semantically_validated": True,
                "structural_verification": {
                    "status": "passed",
                    "causal_anchor_ref": "event:523",
                    "first_bad_event": "event:523",
                    "probe_results": [
                        {
                            "probe_id": "hair_hotspot",
                            "before": [0.21, 0.19, 0.18, 1.0],
                            "after": [0.37, 0.34, 0.32, 1.0],
                        }
                    ],
                    "anomaly_cleared": True,
                    "blocked_by_capability": False,
                    "blocked_capability_codes": [],
                },
                "semantic_verification": {
                    "status": "passed",
                    "verification_mode": "device_parity",
                    "baseline_source_kind": "capture_baseline",
                    "baseline_source_ref": "capture:baseline",
                    "probe_summary": [{"probe_id": "hair_hotspot", "max_delta": 0.03}],
                    "max_delta": 0.03,
                    "fallback_only": False,
                },
                "overall_result": {
                    "status": "passed",
                    "derived_from": ["structural_verification", "semantic_verification"],
                    "verdict": "root_cause_validated_fix_verified",
                },
            },
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    _write(run_root / "notes" / "pixel_forensics.md", "# pixel forensics\n")
    intent_gate = {
        "classifier_version": 1,
        "judged_by": "rdc-debugger",
        "clarification_rounds": 0,
        "normalized_user_goal": "validate fixture",
        "primary_completion_question": "what caused the rendering defect and whether the fix is valid",
        "dominant_operation": "verify_fix",
        "requested_artifact": "fix_verification",
        "ab_role": "evidence_method",
        "scores": {"debugger": 9, "analyst": 1, "optimizer": 0},
        "decision": "debugger",
        "confidence": "high",
        "hard_signals": {
            "debugger_positive": ["fix verification requested"],
            "analyst_positive": [],
            "optimizer_positive": [],
            "disqualifiers": [],
        },
        "rationale": "A/B is only being used to prove the defect cause and fix validity.",
        "redirect_target": "",
    }
    if intent_gate_override is not None:
        intent_gate.update(intent_gate_override)
    _write(
        run_root / "notes" / "hypothesis_board.yaml",
        yaml.safe_dump(
            {
                "hypothesis_board": {
                    "session_id": "sess_fixture_001",
                    "entry_skill": "rdc-debugger",
                    "user_goal": "validate fixture",
                    "intake_state": "validation",
                    "current_phase": "validation",
                    "current_task": "review fixture validation artifacts",
                    "active_owner": "rdc-debugger",
                    "pending_requirements": [],
                    "blocking_issues": [],
                    "progress_summary": ["case initialized", "artifacts written"],
                    "next_actions": ["run compliance audit"],
                    "last_updated": "2026-03-24T00:00:00Z",
                    "intent_gate": intent_gate,
                    "hypotheses": [],
                }
            },
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    _write(
        run_root / "reports" / "report.md",
        "\n".join(
            [
                "# BUG-PREC-FIXTURE",
                "",
                "session_id = sess_fixture_001",
                "capture_file_id = capf_fixture_001",
                "event 523",
                "DEBUGGER_FINAL_VERDICT",
            ]
        )
        + "\n",
    )
    _write(run_root / "reports" / "visual_report.html", "<html><body><p>session_id = sess_fixture_001</p><p>event 523</p></body></html>\n")
    _seed_entry_gate(root, run_root, platform=platform, entry_mode=entry_mode, single_agent_by_user=single_agent_by_user)
    _seed_intake_gate(root, run_root)
    action_chain = root / "common" / "knowledge" / "library" / "sessions" / "sess_fixture_001" / "action_chain.jsonl"
    if action_chain.is_file():
        events = [json.loads(line) for line in action_chain.read_text(encoding="utf-8").splitlines() if line.strip()]
        for event in events:
            payload = event.get("payload")
            if isinstance(payload, dict) and str(event.get("event_type", "")).strip() in {"dispatch", "tool_execution", "artifact_write", "quality_check"}:
                payload["entry_mode"] = entry_mode
                payload["backend"] = "local"
        _write(action_chain, "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n")
        _seed_runtime_topology(root, run_root, platform=platform)
    return run_root


class _ProcResult:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _run_audit(root: Path, platform: str, run_root: Path) -> _ProcResult:
    module = _load_module(AUDIT_SCRIPT, f"run_compliance_audit_module_{platform}_{run_root.name}")
    try:
        payload = module.run_audit(root, run_root, platform)
    except Exception as exc:  # noqa: BLE001
        return _ProcResult(2, "", str(exc))

    action_chain_path = Path(payload["paths"]["action_chain"])
    module._append_event(  # noqa: SLF001
        action_chain_path,
        {
            "schema_version": module.ACTION_CHAIN_SCHEMA,
            "event_id": f"evt-audit-run-compliance-{payload['status']}",
            "ts_ms": module._now_ms(),  # noqa: SLF001
            "run_id": str((yaml.safe_load((run_root / "run.yaml").read_text(encoding="utf-8")) or {}).get("run_id", "")),
            "session_id": payload["session_id"],
            "agent_id": "rdc-debugger",
            "event_type": "quality_check",
            "status": "pass" if payload["status"] == "passed" else "fail",
            "duration_ms": 0,
            "refs": [],
            "payload": _rt_payload(
                validator="run_compliance_audit",
                summary=f"run compliance audit {payload['status']}",
                path=f"workspace/cases/{run_root.parent.parent.name}/runs/{run_root.name}/artifacts/run_compliance.yaml",
            ),
        },
    )
    module._dump_yaml(run_root / "artifacts" / "run_compliance.yaml", payload)  # noqa: SLF001
    stdout = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    return _ProcResult(0 if payload["status"] == "passed" else 1, stdout, "")


class RunComplianceAuditTests(unittest.TestCase):
    def _temp_root(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def test_compliant_run_passes_emits_proposal_and_metrics(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(
            root,
            "case_001",
            "run_01",
            "code-buddy",
            "concurrent_team",
            knowledge_context={
                "matched_sop_id": "SOP-PREC-01",
                "sop_adherence_score": 0.62,
                "symptom_tags": ["banding"],
                "trigger_tags": ["Adreno_GPU"],
                "resolved_invariants": ["I-PREC-01"],
                "invariant_explains_verdict": True,
            },
        )

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "passed")
        self.assertEqual(artifact["metrics"]["tool_execution"]["success"], 1)
        self.assertEqual(artifact["metrics"]["conflicts"]["arbitrated"], 1)
        self.assertEqual(artifact["metrics"]["counterfactual_reviews"]["independent_review_coverage"], 1.0)
        self.assertEqual(artifact["metrics"]["knowledge_candidates"]["emitted"], 1)
        proposals = list((root / "common" / "knowledge" / "proposals").glob("CAND-SOP-*.yaml"))
        self.assertEqual(len(proposals), 1)
        proposal = yaml.safe_load(proposals[0].read_text(encoding="utf-8"))
        self.assertEqual(proposal["schema_version"], "2")
        self.assertEqual(proposal["status"], "candidate")

    def test_audit_only_platform_passes(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "staged_handoff")

        proc = _run_audit(root, "codex", run_root)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "passed")

    def test_same_proposer_and_reviewer_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01", reviewer="shader_ir_agent")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "failed")

    def test_unresolved_conflict_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01", conflict_status="OPEN", hypothesis_status="CONFLICTED")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "failed")
        self.assertEqual(artifact["metrics"]["conflicts"]["arbitrated"], 0)

    def test_missing_review_event_reference_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01", review_event_id="evt-missing-review")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "failed")

    def test_failed_run_does_not_emit_proposal(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01", reviewer="shader_ir_agent")
        run_root = _seed_run(
            root,
            "case_001",
            "run_01",
            "code-buddy",
            "concurrent_team",
            knowledge_context={
                "matched_sop_id": "",
                "sop_adherence_score": 0.40,
                "symptom_tags": ["banding"],
                "trigger_tags": ["Adreno_GPU"],
                "resolved_invariants": ["I-PREC-01"],
                "invariant_explains_verdict": False,
            },
        )

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        proposals = list((root / "common" / "knowledge" / "proposals").glob("CAND-*.yaml"))
        self.assertEqual(proposals, [])

    def test_missing_case_input_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")
        (run_root.parent.parent / "case_input.yaml").unlink()

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "failed")

    def test_missing_capture_manifest_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")
        (run_root.parent.parent / "inputs" / "captures" / "manifest.yaml").unlink()

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("captures_manifest", failing)
        self.assertIn("capture_manifest_integrity", failing)

    def test_missing_imported_capture_file_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")
        (run_root.parent.parent / "inputs" / "captures" / "broken.rdc").unlink()

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("capture_manifest_integrity", failing)
        self.assertIn("intake_gate_status", failing)

    def test_missing_capture_refs_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")
        (run_root / "capture_refs.yaml").unlink()

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("capture_refs", failing)
        self.assertIn("capture_refs_integrity", failing)

    def test_tool_execution_before_intake_gate_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")
        action_chain = root / "common" / "knowledge" / "library" / "sessions" / "sess_fixture_001" / "action_chain.jsonl"
        events = [json.loads(line) for line in action_chain.read_text(encoding="utf-8").splitlines() if line.strip()]
        reordered = [events[1], events[0], *events[2:]]
        _write(action_chain, "\n".join(json.dumps(event, ensure_ascii=False) for event in reordered) + "\n")

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("intake_gate_before_analysis", failing)

    def test_concurrent_team_requires_distinct_contexts_for_distinct_specialists(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")
        action_chain = root / "common" / "knowledge" / "library" / "sessions" / "sess_fixture_001" / "action_chain.jsonl"
        events = [json.loads(line) for line in action_chain.read_text(encoding="utf-8").splitlines() if line.strip()]
        events.append(
            {
                "schema_version": "2",
                "event_id": "evt-0011-second-tool",
                "ts_ms": 1772537603000,
                "run_id": "run_01",
                "session_id": "sess_fixture_001",
                "agent_id": "shader_ir_agent",
                "event_type": "tool_execution",
                "status": "ok",
                "duration_ms": 90,
                "refs": ["evt-0002-dispatch"],
                "payload": _rt_payload(
                    context_id="ctx-pixel",
                    runtime_owner="shader_ir_agent",
                    tool_name="rd.shader.debug_start",
                    transport="daemon",
                ),
            }
        )
        _write(action_chain, "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n")

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("runtime_owner_topology", failing)

    def test_runtime_topology_records_platform_agentic_profile(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "staged_handoff")

        artifact = yaml.safe_load((run_root / "artifacts" / "runtime_topology.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["sub_agent_mode"], "puppet_sub_agents")
        self.assertEqual(artifact["peer_communication"], "via_main_agent")
        self.assertEqual(artifact["dispatch_topology"], "hub_and_spoke")
        self.assertEqual(artifact["specialist_dispatch_requirement"], "required")
        self.assertEqual(artifact["host_delegation_policy"], "platform_managed")
        self.assertEqual(artifact["host_delegation_fallback"], "none")
        self.assertEqual(artifact["orchestration_mode"], "multi_agent")
        self.assertEqual(artifact["single_agent_reason"], "")
        self.assertEqual(artifact["runtime_parallelism_ceiling"], "multi_context_multi_owner")
        self.assertEqual(artifact["applied_live_runtime_policy"], "multi_context_orchestrated")
        self.assertEqual(artifact["delegation_status"], "native_dispatch")
        self.assertEqual(artifact["fallback_execution_mode"], "wrapper")
        self.assertEqual(artifact["workflow_stage"], "fix_verification_complete")
        self.assertEqual(artifact["degraded_reasons"], [])
        self.assertTrue(artifact["context_bindings"])
        pixel_binding = next(item for item in artifact["context_bindings"] if item["context_id"] == "ctx-pixel")
        self.assertEqual(pixel_binding["owner_agent"], "pixel_forensics_agent")
        self.assertEqual(pixel_binding["capture_ref"], "capture:anomalous")
        self.assertEqual(pixel_binding["canonical_anchor_ref"], "event:523")
        self.assertTrue(pixel_binding["session_locator"]["rdc_path"].endswith("broken.rdc"))

    def test_staged_handoff_local_allows_distinct_specialist_contexts(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "staged_handoff")

        action_chain = root / "common" / "knowledge" / "library" / "sessions" / "sess_fixture_001" / "action_chain.jsonl"
        events = [json.loads(line) for line in action_chain.read_text(encoding="utf-8").splitlines() if line.strip()]
        events.append(
            {
                "schema_version": "2",
                "event_id": "evt-0011-dispatch-shader",
                "ts_ms": 1772537603000,
                "run_id": "run_01",
                "session_id": "sess_fixture_001",
                "agent_id": "rdc-debugger",
                "event_type": "dispatch",
                "status": "sent",
                "duration_ms": 10,
                "refs": ["evt-0004-specialist-artifact"],
                "payload": _rt_payload(
                    context_id="ctx-orchestrator",
                    runtime_owner="rdc-debugger",
                    target_agent="shader_ir_agent",
                    objective="inspect shader precision path",
                    task_scope="shader precision path",
                ),
            }
        )
        events.append(
            {
                "schema_version": "2",
                "event_id": "evt-0012-shader-tool",
                "ts_ms": 1772537603200,
                "run_id": "run_01",
                "session_id": "sess_fixture_001",
                "agent_id": "shader_ir_agent",
                "event_type": "tool_execution",
                "status": "ok",
                "duration_ms": 90,
                "refs": ["evt-0011-dispatch-shader"],
                "payload": _rt_payload(
                    context_id="ctx-shader",
                    runtime_owner="shader_ir_agent",
                    tool_name="rd.shader.debug_start",
                    transport="daemon",
                    capture_ref="capture:baseline",
                    canonical_anchor_ref="event:640",
                    task_scope="shader debug",
                ),
            }
        )
        events.append(
            {
                "schema_version": "2",
                "event_id": "evt-0013-shader-artifact",
                "ts_ms": 1772537603400,
                "run_id": "run_01",
                "session_id": "sess_fixture_001",
                "agent_id": "shader_ir_agent",
                "event_type": "artifact_write",
                "status": "written",
                "duration_ms": 12,
                "refs": ["evt-0012-shader-tool"],
                "payload": _rt_payload(
                    context_id="ctx-shader",
                    runtime_owner="shader_ir_agent",
                    path=f"workspace/cases/{run_root.parent.parent.name}/runs/{run_root.name}/notes/shader_ir.md",
                    artifact_role="specialist_handoff",
                    capture_ref="capture:baseline",
                    canonical_anchor_ref="event:640",
                    task_scope="shader handoff",
                ),
            }
        )
        _write(action_chain, "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n")
        _seed_runtime_topology(root, run_root, platform="codex")

        proc = _run_audit(root, "codex", run_root)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "passed")

    def test_staged_handoff_local_reused_context_for_distinct_specialists_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "staged_handoff")

        action_chain = root / "common" / "knowledge" / "library" / "sessions" / "sess_fixture_001" / "action_chain.jsonl"
        events = [json.loads(line) for line in action_chain.read_text(encoding="utf-8").splitlines() if line.strip()]
        events.append(
            {
                "schema_version": "2",
                "event_id": "evt-0011-dispatch-shader",
                "ts_ms": 1772537603000,
                "run_id": "run_01",
                "session_id": "sess_fixture_001",
                "agent_id": "rdc-debugger",
                "event_type": "dispatch",
                "status": "sent",
                "duration_ms": 10,
                "refs": ["evt-0004-specialist-artifact"],
                "payload": _rt_payload(
                    context_id="ctx-orchestrator",
                    runtime_owner="rdc-debugger",
                    target_agent="shader_ir_agent",
                    objective="inspect shader precision path",
                    task_scope="shader precision path",
                ),
            }
        )
        events.append(
            {
                "schema_version": "2",
                "event_id": "evt-0012-shader-tool",
                "ts_ms": 1772537603200,
                "run_id": "run_01",
                "session_id": "sess_fixture_001",
                "agent_id": "shader_ir_agent",
                "event_type": "tool_execution",
                "status": "ok",
                "duration_ms": 90,
                "refs": ["evt-0011-dispatch-shader"],
                "payload": _rt_payload(
                    context_id="ctx-pixel",
                    runtime_owner="shader_ir_agent",
                    tool_name="rd.shader.debug_start",
                    transport="daemon",
                    context_binding_id="ctxbind-ctx-pixel-shader",
                    capture_ref="capture:baseline",
                    canonical_anchor_ref="event:640",
                    task_scope="shader debug",
                ),
            }
        )
        _write(action_chain, "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n")
        _seed_runtime_topology(root, run_root, platform="codex")

        proc = _run_audit(root, "codex", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("runtime_owner_topology", failing)
        topology = yaml.safe_load((run_root / "artifacts" / "runtime_topology.yaml").read_text(encoding="utf-8"))
        self.assertEqual(topology["remote_context_locality"], "strict")
        self.assertEqual(topology["remote_handle_reuse_policy"], "must_reconnect")
        self.assertEqual(topology["remote_gate_status"]["prerequisite"]["status"], "passed")

    def test_staged_handoff_specialist_cannot_dispatch_specialist(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "staged_handoff")

        action_chain = root / "common" / "knowledge" / "library" / "sessions" / "sess_fixture_001" / "action_chain.jsonl"
        events = [json.loads(line) for line in action_chain.read_text(encoding="utf-8").splitlines() if line.strip()]
        events.append(
            {
                "schema_version": "2",
                "event_id": "evt-0011-bad-specialist-dispatch",
                "ts_ms": 1772537603000,
                "run_id": "run_01",
                "session_id": "sess_fixture_001",
                "agent_id": "pixel_forensics_agent",
                "event_type": "dispatch",
                "status": "sent",
                "duration_ms": 5,
                "refs": ["evt-0003-tool"],
                "payload": _rt_payload(
                    context_id="ctx-pixel",
                    runtime_owner="pixel_forensics_agent",
                    target_agent="shader_ir_agent",
                    objective="illegal peer dispatch",
                    task_scope="illegal peer dispatch",
                ),
            }
        )
        _write(action_chain, "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n")
        _seed_runtime_topology(root, run_root, platform="codex")

        proc = _run_audit(root, "codex", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("runtime_owner_topology", failing)

    def test_runtime_topology_records_single_agent_by_user_fields(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "staged_handoff", single_agent_by_user=True)
        topology = yaml.safe_load((run_root / "artifacts" / "runtime_topology.yaml").read_text(encoding="utf-8"))
        entry_gate = yaml.safe_load((run_root.parent.parent / "artifacts" / "entry_gate.yaml").read_text(encoding="utf-8"))
        self.assertEqual(entry_gate["orchestration_mode"], "single_agent_by_user")
        self.assertEqual(entry_gate["single_agent_reason"], "user_requested")
        self.assertEqual(topology["orchestration_mode"], "single_agent_by_user")
        self.assertEqual(topology["single_agent_reason"], "user_requested")
        self.assertEqual(topology["delegation_status"], "single_agent_by_user")

    def test_single_agent_mode_with_specialist_events_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "staged_handoff", single_agent_by_user=True)

        proc = _run_audit(root, "codex", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("delegation_execution_contract", failing)

    def test_specialist_feedback_timeout_blocker_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "staged_handoff")

        board = yaml.safe_load((run_root / "notes" / "hypothesis_board.yaml").read_text(encoding="utf-8"))
        board["hypothesis_board"]["blocking_issues"] = ["BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT"]
        _write(run_root / "notes" / "hypothesis_board.yaml", yaml.safe_dump(board, sort_keys=False, allow_unicode=True))

        proc = _run_audit(root, "codex", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("hypothesis_board_blockers", failing)

    def test_missing_visual_report_html_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "staged_handoff")
        (run_root / "reports" / "visual_report.html").unlink()

        proc = _run_audit(root, "codex", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("visual_report_html", failing)

    def test_cross_context_transfer_without_baton_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "staged_handoff")

        action_chain = root / "common" / "knowledge" / "library" / "sessions" / "sess_fixture_001" / "action_chain.jsonl"
        events = [json.loads(line) for line in action_chain.read_text(encoding="utf-8").splitlines() if line.strip()]
        events.append(
            {
                "schema_version": "2",
                "event_id": "evt-0011-cross-context-transfer",
                "ts_ms": 1772537603000,
                "run_id": "run_01",
                "session_id": "sess_fixture_001",
                "agent_id": "shader_ir_agent",
                "event_type": "tool_execution",
                "status": "ok",
                "duration_ms": 70,
                "refs": ["evt-0002-dispatch"],
                "payload": _rt_payload(
                    context_id="ctx-shader",
                    runtime_owner="shader_ir_agent",
                    tool_name="rd.session.resume",
                    source_context_id="ctx-pixel",
                    baton_ref="",
                    capture_ref="capture:baseline",
                    canonical_anchor_ref="event:640",
                    task_scope="cross-context resume",
                ),
            }
        )
        _write(action_chain, "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n")
        _seed_runtime_topology(root, run_root, platform="codex")

        proc = _run_audit(root, "codex", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("runtime_baton_contract", failing)

    def test_remote_run_requires_single_runtime_owner(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "staged_handoff")

        entry_gate = yaml.safe_load((run_root.parent.parent / "artifacts" / "entry_gate.yaml").read_text(encoding="utf-8"))
        entry_gate["backend"] = "remote"
        entry_gate["request"]["remote_transport"] = "adb_android"
        _write(run_root.parent.parent / "artifacts" / "entry_gate.yaml", yaml.safe_dump(entry_gate, sort_keys=False, allow_unicode=True))
        run_yaml = yaml.safe_load((run_root / "run.yaml").read_text(encoding="utf-8"))
        run_yaml["runtime"]["backend"] = "remote"
        _write(run_root / "run.yaml", yaml.safe_dump(run_yaml, sort_keys=False, allow_unicode=True))
        _seed_remote_artifacts(run_root)
        _seed_runtime_topology(root, run_root, platform="codex")

        action_chain = root / "common" / "knowledge" / "library" / "sessions" / "sess_fixture_001" / "action_chain.jsonl"
        events = [json.loads(line) for line in action_chain.read_text(encoding="utf-8").splitlines() if line.strip()]
        events.append(
            {
                "schema_version": "2",
                "event_id": "evt-0011-remote-owner",
                "ts_ms": 1772537603100,
                "run_id": "run_01",
                "session_id": "sess_fixture_001",
                "agent_id": "shader_ir_agent",
                "event_type": "tool_execution",
                "status": "ok",
                "duration_ms": 90,
                "refs": ["evt-0002-dispatch"],
                "payload": _rt_payload(
                    backend="remote",
                    context_id="ctx-remote",
                    runtime_owner="shader_ir_agent",
                    tool_name="rd.event.get_actions",
                    transport="daemon",
                ),
            }
        )
        _write(action_chain, "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n")

        proc = _run_audit(root, "codex", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("runtime_owner_topology", failing)

    def test_remote_run_missing_remote_artifacts_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "staged_handoff")

        entry_gate = yaml.safe_load((run_root.parent.parent / "artifacts" / "entry_gate.yaml").read_text(encoding="utf-8"))
        entry_gate["backend"] = "remote"
        entry_gate["request"]["remote_transport"] = "adb_android"
        _write(run_root.parent.parent / "artifacts" / "entry_gate.yaml", yaml.safe_dump(entry_gate, sort_keys=False, allow_unicode=True))
        run_yaml = yaml.safe_load((run_root / "run.yaml").read_text(encoding="utf-8"))
        run_yaml["runtime"]["backend"] = "remote"
        _write(run_root / "run.yaml", yaml.safe_dump(run_yaml, sort_keys=False, allow_unicode=True))
        _seed_runtime_topology(root, run_root, platform="codex")

        proc = _run_audit(root, "codex", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("remote_prerequisite_gate_artifact", failing)
        self.assertIn("remote_capability_gate_artifact", failing)
        self.assertIn("remote_recovery_decision_artifact", failing)

    def test_invalid_fix_verdict_fails_schema(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")
        fix_path = run_root / "artifacts" / "fix_verification.yaml"
        payload = yaml.safe_load(fix_path.read_text(encoding="utf-8"))
        payload["verdict"] = "legacy_verdict"
        payload["overall_result"]["verdict"] = "legacy_verdict"
        fix_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("fix_verification_schema", failing)

    def test_waiting_for_specialist_brief_overreach_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "staged_handoff")
        action_chain = root / "common" / "knowledge" / "library" / "sessions" / "sess_fixture_001" / "action_chain.jsonl"
        events = [json.loads(line) for line in action_chain.read_text(encoding="utf-8").splitlines() if line.strip()]
        events.insert(
            1,
            {
                "schema_version": "2",
                "event_id": "evt-0001b-waiting",
                "ts_ms": 1772537599950,
                "run_id": "run_01",
                "session_id": "sess_fixture_001",
                "agent_id": "rdc-debugger",
                "event_type": "workflow_stage_transition",
                "status": "entered",
                "duration_ms": 0,
                "refs": [],
                "payload": {
                    "workflow_stage": "waiting_for_specialist_brief",
                    "blocking_code": "",
                    "blocking_codes": [],
                    "required_artifacts_before_transition": ["notes/pixel_forensics.md"],
                },
            },
        )
        events.insert(
            2,
            {
                "schema_version": "2",
                "event_id": "evt-0001c-overreach",
                "ts_ms": 1772537599960,
                "run_id": "run_01",
                "session_id": "sess_fixture_001",
                "agent_id": "rdc-debugger",
                "event_type": "tool_execution",
                "status": "ok",
                "duration_ms": 30,
                "refs": [],
                "payload": _rt_payload(
                    context_id="ctx-orchestrator",
                    runtime_owner="rdc-debugger",
                    tool_name="rd.pipeline.get_state",
                    transport="daemon",
                ),
            },
        )
        events.insert(
            3,
            {
                "schema_version": "2",
                "event_id": "evt-0001d-briefs-collected",
                "ts_ms": 1772537599970,
                "run_id": "run_01",
                "session_id": "sess_fixture_001",
                "agent_id": "rdc-debugger",
                "event_type": "workflow_stage_transition",
                "status": "entered",
                "duration_ms": 0,
                "refs": [],
                "payload": {
                    "workflow_stage": "specialist_briefs_collected",
                    "blocking_code": "",
                    "blocking_codes": [],
                    "required_artifacts_before_transition": ["notes/pixel_forensics.md"],
                },
            },
        )
        _write(action_chain, "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n")
        _seed_runtime_topology(root, run_root, platform="codex")

        proc = _run_audit(root, "codex", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("workflow_stage_overreach", failing)

    def test_resume_without_baton_ref_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")
        action_chain = root / "common" / "knowledge" / "library" / "sessions" / "sess_fixture_001" / "action_chain.jsonl"
        events = [json.loads(line) for line in action_chain.read_text(encoding="utf-8").splitlines() if line.strip()]
        events[2]["payload"]["tool_name"] = "rd.session.resume"
        events[2]["payload"]["baton_ref"] = ""
        _write(action_chain, "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n")

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("runtime_baton_contract", failing)

    def test_specialist_cannot_execute_live_tool_with_other_runtime_owner(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")
        action_chain = root / "common" / "knowledge" / "library" / "sessions" / "sess_fixture_001" / "action_chain.jsonl"
        events = [json.loads(line) for line in action_chain.read_text(encoding="utf-8").splitlines() if line.strip()]
        events[2]["payload"]["runtime_owner"] = "rdc-debugger"
        _write(action_chain, "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n")

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        failing = {item["id"] for item in artifact["checks"] if item["result"] == "fail"}
        self.assertIn("runtime_owner_topology", failing)

    def test_fallback_only_fix_verification_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")
        fix_path = run_root / "artifacts" / "fix_verification.yaml"
        payload = yaml.safe_load(fix_path.read_text(encoding="utf-8"))
        payload["semantic_verification"]["status"] = "fallback_only"
        payload["overall_result"]["status"] = "failed"
        fix_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "failed")

    def test_missing_intent_gate_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")

        payload = yaml.safe_load((run_root / "notes" / "hypothesis_board.yaml").read_text(encoding="utf-8"))
        payload["hypothesis_board"].pop("intent_gate", None)
        _write(run_root / "notes" / "hypothesis_board.yaml", yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

    def test_non_debugger_intent_gate_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(
            root,
            "case_001",
            "run_01",
            "code-buddy",
            "concurrent_team",
            intent_gate_override={"decision": "analyst", "redirect_target": "rdc-analyst"},
        )

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

    def test_redirect_target_must_be_empty_for_debugger_run(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root = _seed_run(
            root,
            "case_001",
            "run_01",
            "code-buddy",
            "concurrent_team",
            intent_gate_override={"redirect_target": "rdc-analyst"},
        )

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

    def test_repeated_candidate_updates_existing_proposal(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        knowledge_context = {
            "matched_sop_id": "SOP-PREC-01",
            "sop_adherence_score": 0.62,
            "symptom_tags": ["banding"],
            "trigger_tags": ["Adreno_GPU"],
            "resolved_invariants": ["I-PREC-01"],
            "invariant_explains_verdict": True,
        }

        _seed_common_session(root, "sess_fixture_001", "run_01")
        run_root_1 = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team", knowledge_context=knowledge_context)
        proc_1 = _run_audit(root, "code-buddy", run_root_1)
        self.assertEqual(proc_1.returncode, 0, proc_1.stdout + proc_1.stderr)

        _seed_common_session(root, "sess_fixture_002", "run_02", case_id="case_002")
        run_root_2 = _seed_run(root, "case_002", "run_02", "code-buddy", "concurrent_team", knowledge_context=knowledge_context)
        run_yaml_2 = yaml.safe_load((run_root_2 / "run.yaml").read_text(encoding="utf-8"))
        run_yaml_2["session_id"] = "sess_fixture_002"
        _write(run_root_2 / "run.yaml", yaml.safe_dump(run_yaml_2, sort_keys=False, allow_unicode=True))
        _write(
            run_root_2 / "reports" / "report.md",
            "\n".join(
                [
                    "# BUG-PREC-FIXTURE",
                    "",
                    "session_id = sess_fixture_002",
                    "capture_file_id = capf_fixture_001",
                    "event 523",
                    "DEBUGGER_FINAL_VERDICT",
                ]
            )
            + "\n",
        )
        _write(run_root_2 / "reports" / "visual_report.html", "<html><body><p>session_id = sess_fixture_002</p><p>event 523</p></body></html>\n")
        _seed_runtime_topology(root, run_root_2, platform="code-buddy")
        proc_2 = _run_audit(root, "code-buddy", run_root_2)
        self.assertEqual(proc_2.returncode, 0, proc_2.stdout + proc_2.stderr)

        proposals = list((root / "common" / "knowledge" / "proposals").glob("CAND-SOP-*.yaml"))
        self.assertEqual(len(proposals), 1)
        proposal = yaml.safe_load(proposals[0].read_text(encoding="utf-8"))
        self.assertEqual(proposal["support_runs"], 2)
        self.assertEqual(sorted(proposal["source_refs"]["run_ids"]), ["run_01", "run_02"])


if __name__ == "__main__":
    unittest.main()
