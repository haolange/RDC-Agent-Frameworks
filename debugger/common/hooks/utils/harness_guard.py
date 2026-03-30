#!/usr/bin/env python3
"""Shared cross-platform harness enforcement core."""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import yaml
except ModuleNotFoundError:
    print("missing dependency 'PyYAML'", file=sys.stderr)
    raise SystemExit(2)


def _debugger_root(default: Path | None = None) -> Path:
    return default.resolve() if default else Path(__file__).resolve().parents[3]


COMMON_UTILS = Path(__file__).resolve().parent
COMMON_VALIDATORS = Path(__file__).resolve().parents[1] / "validators"
COMMON_CONFIG = Path(__file__).resolve().parents[2] / "config"
for path in (COMMON_UTILS, COMMON_VALIDATORS, COMMON_CONFIG):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

from entry_gate import run_entry_gate as shared_run_entry_gate  # noqa: E402
from hypothesis_board_validator import validate_hypothesis_board  # noqa: E402
from intake_gate import build_intake_gate_payload, run_intake_gate as shared_run_intake_gate  # noqa: E402
from run_compliance_audit import (  # noqa: E402
    ACTION_CHAIN_SCHEMA,
    ACTION_SPECIALISTS,
    load_action_chain_events,
    specialist_handoff_path_ok,
    workflow_stage_overreach_issues,
    write_run_audit_artifact,
)
from runtime_topology import (  # noqa: E402
    build_runtime_topology_payload,
    run_runtime_topology as shared_run_runtime_topology,
)
from validate_binding import validate_binding  # noqa: E402
from validate_tool_contract_runtime import validate_runtime_tool_contract  # noqa: E402


GUARD_SCHEMA = "2"
CAPABILITY_TOKEN_SCHEMA = "1"
QUALITY_CHECK_EVENT_TYPE = "quality_check"
PROCESS_DEVIATION_EVENT_TYPE = "process_deviation"
DISPATCH_FEEDBACK_EVENT_TYPES = {
    "artifact_write",
    "quality_check",
    "counterfactual_reviewed",
    "conflict_resolved",
}
SPECIALIST_TOKEN_AGENTS = ACTION_SPECIALISTS | {"skeptic_agent", "curator_agent"}
DEFAULT_TOKEN_TTL_SECONDS = 1800
DEFAULT_TOKEN_ACTIONS = ("write_note", "live_investigation", "submit_brief")
NOTE_FILE_BY_AGENT = {
    "triage_agent": "triage.md",
    "capture_repro_agent": "capture_repro.md",
    "pass_graph_pipeline_agent": "pass_graph_pipeline.md",
    "pixel_forensics_agent": "pixel_forensics.md",
    "shader_ir_agent": "shader_ir.md",
    "driver_device_agent": "driver_device.md",
    "skeptic_agent": "skeptic.md",
    "curator_agent": "curator.md",
}


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def _dump_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="ignore")


def _norm(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _now_ms() -> int:
    return int(_now().timestamp() * 1000)


def _status_ok(value: str) -> bool:
    return str(value or "").strip() in {"passed", "ready", "not_applicable"}


def _sanitize_token(value: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "-" for ch in str(value or "").strip())
    text = text.strip("-_")
    return text or "unknown"


def _extract_session_id(root: Path, run_root: Path) -> str:
    run_yaml = run_root / "run.yaml"
    run_data = _read_yaml(run_yaml) if run_yaml.is_file() else {}
    if not isinstance(run_data, dict):
        run_data = {}
    for value in (
        run_data.get("session_id"),
        (run_data.get("debug") or {}).get("session_id") if isinstance(run_data.get("debug"), dict) else None,
        (run_data.get("runtime") or {}).get("session_id") if isinstance(run_data.get("runtime"), dict) else None,
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    session_marker = root / "common" / "knowledge" / "library" / "sessions" / ".current_session"
    if session_marker.is_file():
        value = session_marker.read_text(encoding="utf-8").lstrip("\ufeff").strip()
        if value and value != "session-unset":
            return value
    return ""


def _action_chain_path(root: Path, run_root: Path) -> Path:
    session_id = _extract_session_id(root, run_root)
    sessions_root = root / "common" / "knowledge" / "library" / "sessions"
    if session_id:
        return sessions_root / session_id / "action_chain.jsonl"
    return sessions_root / "action_chain.jsonl"


def _action_chain_events(root: Path, run_root: Path) -> list[dict[str, Any]]:
    path = _action_chain_path(root, run_root)
    return load_action_chain_events(path) if path.is_file() else []


def _append_event(path: Path, event: dict[str, Any]) -> None:
    serialized = json.dumps(event, ensure_ascii=False)
    existing = _read_text(path) if path.exists() else ""
    if serialized in existing:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(serialized)
        handle.write("\n")


def _runtime_fields(run_root: Path) -> dict[str, str]:
    topology_path = run_root / "artifacts" / "runtime_topology.yaml"
    topology = _read_yaml(topology_path) if topology_path.is_file() else {}
    if not isinstance(topology, dict):
        topology = {}
    bindings = list(topology.get("context_bindings") or [])
    first_binding = bindings[0] if bindings else {}
    contexts = list(topology.get("contexts") or [])
    owners = list(topology.get("owners") or [])
    return {
        "entry_mode": str(topology.get("entry_mode") or "cli").strip() or "cli",
        "backend": str(topology.get("backend") or "local").strip() or "local",
        "context_id": str((contexts or ["default"])[0]),
        "runtime_owner": str((owners or ["rdc-debugger"])[0]),
        "baton_ref": "",
        "context_binding_id": str(first_binding.get("context_binding_id") or "ctxbind-default"),
        "capture_ref": str(first_binding.get("capture_ref") or ""),
        "canonical_anchor_ref": str(first_binding.get("canonical_anchor_ref") or ""),
    }


def _run_id(run_root: Path) -> str:
    run_yaml = run_root / "run.yaml"
    if not run_yaml.is_file():
        return run_root.name
    data = _read_yaml(run_yaml)
    if not isinstance(data, dict):
        return run_root.name
    return str(data.get("run_id") or run_root.name).strip() or run_root.name


def _write_guard_artifact(run_root: Path, artifact_name: str, payload: dict[str, Any]) -> Path:
    path = run_root / "artifacts" / artifact_name
    _dump_yaml(path, payload)
    return path


def _guard_payload(
    *,
    stage: str,
    status: str,
    blockers: list[dict[str, Any]],
    refs: list[str] | None = None,
    paths: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": GUARD_SCHEMA,
        "generated_by": "harness_guard",
        "generated_at": _now_iso(),
        "guard_stage": stage,
        "status": status,
        "blocking_codes": [str(item.get("code") or "").strip() for item in blockers if str(item.get("code") or "").strip()],
        "blockers": blockers,
        **({"refs": refs} if refs else {}),
        **({"paths": paths} if paths else {}),
        **(extra or {}),
    }


def _emit_quality_check(root: Path, run_root: Path, *, stage: str, payload: dict[str, Any], artifact_path: Path) -> None:
    action_chain = _action_chain_path(root, run_root)
    runtime = _runtime_fields(run_root)
    _append_event(
        action_chain,
        {
            "schema_version": ACTION_CHAIN_SCHEMA,
            "event_id": f"evt-harness-guard-{stage}-{payload['status']}-{_now_ms()}",
            "ts_ms": _now_ms(),
            "run_id": _run_id(run_root),
            "session_id": _extract_session_id(root, run_root),
            "agent_id": "rdc-debugger",
            "event_type": QUALITY_CHECK_EVENT_TYPE,
            "status": "pass" if payload["status"] == "passed" else "fail",
            "duration_ms": 0,
            "refs": [],
            "payload": {
                "validator": "harness_guard",
                "guard_stage": stage,
                "summary": f"harness guard {stage} {payload['status']}",
                "path": _norm(artifact_path),
                "blocking_codes": list(payload.get("blocking_codes") or []),
                **runtime,
            },
        },
    )


def _emit_process_deviation(
    root: Path,
    run_root: Path,
    *,
    deviation_code: str,
    summary: str,
    refs: list[str],
    artifact_path: Path,
) -> None:
    action_chain = _action_chain_path(root, run_root)
    runtime = _runtime_fields(run_root)
    _append_event(
        action_chain,
        {
            "schema_version": ACTION_CHAIN_SCHEMA,
            "event_id": f"evt-harness-process-deviation-{_now_ms()}",
            "ts_ms": _now_ms(),
            "run_id": _run_id(run_root),
            "session_id": _extract_session_id(root, run_root),
            "agent_id": "rdc-debugger",
            "event_type": PROCESS_DEVIATION_EVENT_TYPE,
            "status": "blocked",
            "duration_ms": 0,
            "refs": refs,
            "payload": {
                "deviation_code": deviation_code,
                "summary": summary,
                "path": _norm(artifact_path),
                **runtime,
            },
        },
    )


def _flatten_tool_contract_findings(root: Path) -> list[str]:
    try:
        findings = validate_runtime_tool_contract(root)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    rows: list[str] = []
    for path, tools in sorted(findings.unknown_tools.items()):
        rows.append(f"{path}: {', '.join(sorted(tools))}")
    rows.extend(findings.missing_prerequisite_examples)
    rows.extend(findings.banned_snippets)
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _guess_capture_role(index: int, total: int) -> str:
    if index == 0:
        return "anomalous"
    if index == 1 and total >= 2:
        return "baseline"
    if index == 2 and total >= 3:
        return "fixed"
    return "fixed" if index == total - 1 and total > 2 else "baseline"


def _guess_capture_source(role: str) -> str:
    return "historical_good" if role == "baseline" else "user_supplied"


def _default_reference_contract(capture_roles: list[str]) -> tuple[str, dict[str, Any]]:
    if "baseline" in capture_roles:
        return (
            "cross_device",
            {
                "source_kind": "capture_baseline",
                "source_refs": ["capture:baseline"],
                "verification_mode": "device_parity",
                "probe_set": {"pixels": [{"name": "intake_probe", "x": 0, "y": 0}]},
                "acceptance": {"fallback_only": False, "max_channel_delta": 0.05},
            },
        )
    return (
        "single",
        {
            "source_kind": "mixed",
            "source_refs": ["capture:anomalous"],
            "verification_mode": "visual_comparison",
            "probe_set": {"pixels": [{"name": "intake_probe", "x": 0, "y": 0}]},
            "acceptance": {"fallback_only": True, "max_channel_delta": 0.05},
        },
    )


def _default_hypothesis_board(session_id: str, user_goal: str, symptom_summary: str) -> dict[str, Any]:
    return {
        "hypothesis_board": {
            "session_id": session_id,
            "entry_skill": "rdc-debugger",
            "user_goal": user_goal,
            "intake_state": "handoff_ready",
            "current_phase": "intake",
            "current_task": symptom_summary,
            "active_owner": "rdc-debugger",
            "pending_requirements": [],
            "blocking_issues": [],
            "progress_summary": ["accepted intake complete"],
            "next_actions": ["run dispatch_readiness before specialist dispatch"],
            "last_updated": _now_iso(),
            "intent_gate": {
                "classifier_version": 1,
                "judged_by": "rdc-debugger",
                "clarification_rounds": 0,
                "normalized_user_goal": user_goal,
                "primary_completion_question": "why is the render wrong",
                "dominant_operation": "diagnose",
                "requested_artifact": "debugger_verdict",
                "ab_role": "evidence_method",
                "scores": {"debugger": 9, "analyst": 0, "optimizer": 0},
                "decision": "debugger",
                "confidence": "high",
                "hard_signals": {
                    "debugger_positive": [],
                    "analyst_positive": [],
                    "optimizer_positive": [],
                    "disqualifiers": [],
                },
                "rationale": symptom_summary,
                "redirect_target": "",
            },
            "hypotheses": [],
        }
    }


def _next_run_id(case_root: Path) -> str:
    runs_root = case_root / "runs"
    existing = {path.name for path in runs_root.iterdir()} if runs_root.is_dir() else set()
    index = 1
    while True:
        candidate = f"run_{index:03d}"
        if candidate not in existing:
            return candidate
        index += 1


def _resolve_case_id(case_root: Path, case_id: str | None = None) -> str:
    if case_id and str(case_id).strip():
        return str(case_id).strip()
    return case_root.name or "case_001"


def _resolve_session_id(case_id: str, run_id: str, session_id: str | None = None) -> str:
    if session_id and str(session_id).strip():
        return str(session_id).strip()
    return f"sess_{_sanitize_token(case_id)}_{_sanitize_token(run_id)}"


def _capture_tokens(case_root: Path, capture_paths: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    refs: list[dict[str, Any]] = []
    roles: list[str] = []
    total = len(capture_paths)
    captures_root = case_root / "inputs" / "captures"
    captures_root.mkdir(parents=True, exist_ok=True)
    for index, raw in enumerate(capture_paths):
        source_path = Path(raw).resolve()
        role = _guess_capture_role(index, total)
        roles.append(role)
        capture_id = f"cap-{role}-{index + 1:03d}"
        dest_name = source_path.name
        dest_path = captures_root / dest_name
        shutil.copy2(source_path, dest_path)
        entries.append(
            {
                "capture_id": capture_id,
                "capture_role": role,
                "file_name": dest_name,
                "source": _guess_capture_source(role),
                "import_mode": "path",
                "imported_at": _now_iso(),
                "sha256": _sha256(dest_path),
                "source_path": _norm(source_path),
            }
        )
        refs.append({"capture_id": capture_id, "capture_role": role})
    return entries, refs, roles


def _default_reference_manifest(reference_contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "references": [
            {
                "reference_id": "reference_contract_intake",
                "source_kind": str(reference_contract.get("source_kind") or "mixed"),
                "source_refs": list(reference_contract.get("source_refs") or []),
                "verification_mode": str(reference_contract.get("verification_mode") or "visual_comparison"),
            }
        ]
    }


def _token_store(run_root: Path) -> Path:
    return run_root / "artifacts" / "capability_tokens"


def _token_path(run_root: Path, token_id: str) -> Path:
    return _token_store(run_root) / f"{token_id}.yaml"


def _allowed_path_match(target_path: str, allowed_paths: list[str]) -> bool:
    normalized_target = _norm(target_path).lower()
    for allowed in allowed_paths:
        normalized_allowed = _norm(allowed).lower()
        if normalized_target == normalized_allowed or normalized_target.startswith(normalized_allowed.rstrip("/") + "/"):
            return True
    return False


def issue_capability_token(
    run_root: Path,
    *,
    target_agent: str,
    runtime_owner: str,
    allowed_actions: list[str] | None = None,
    allowed_paths: list[str] | None = None,
    ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
    issued_by: str = "rdc-debugger",
) -> dict[str, Any]:
    token_id = f"tok-{_sanitize_token(target_agent)}-{secrets.token_hex(6)}"
    payload = {
        "schema_version": CAPABILITY_TOKEN_SCHEMA,
        "token_id": token_id,
        "run_id": _run_id(run_root),
        "target_agent": target_agent,
        "runtime_owner": runtime_owner,
        "allowed_actions": list(allowed_actions or DEFAULT_TOKEN_ACTIONS),
        "allowed_paths": list(allowed_paths or []),
        "ttl_seconds": int(ttl_seconds),
        "issued_at": _now_iso(),
        "expires_at": (_now() + timedelta(seconds=int(ttl_seconds))).isoformat(),
        "issued_by": issued_by,
        "nonce": secrets.token_hex(16),
        "status": "active",
        "path": _norm(_token_path(run_root, token_id)),
    }
    _dump_yaml(_token_path(run_root, token_id), payload)
    return payload


def validate_capability_token(
    run_root: Path,
    *,
    token_ref: str,
    agent_id: str,
    runtime_owner: str,
    action: str,
    target_path: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    token_path = Path(token_ref)
    if not token_path.is_absolute():
        token_path = (run_root / token_ref).resolve()
    if not token_path.is_file():
        return {
            "status": "blocked",
            "blocking_code": "BLOCKED_CAPABILITY_TOKEN_REQUIRED",
            "reason": "capability token file is missing",
            "path": _norm(token_path),
        }
    token = _read_yaml(token_path)
    if not isinstance(token, dict):
        return {
            "status": "blocked",
            "blocking_code": "BLOCKED_CAPABILITY_TOKEN_INVALID",
            "reason": "capability token payload must be a YAML object",
            "path": _norm(token_path),
        }
    current = now or _now()
    expires_at = str(token.get("expires_at") or "").strip()
    if not expires_at:
        return {
            "status": "blocked",
            "blocking_code": "BLOCKED_CAPABILITY_TOKEN_INVALID",
            "reason": "capability token is missing expires_at",
            "path": _norm(token_path),
        }
    if current > datetime.fromisoformat(expires_at):
        return {
            "status": "blocked",
            "blocking_code": "BLOCKED_CAPABILITY_TOKEN_EXPIRED",
            "reason": "capability token has expired",
            "path": _norm(token_path),
        }
    if str(token.get("target_agent") or "").strip() != agent_id:
        return {
            "status": "blocked",
            "blocking_code": "BLOCKED_CAPABILITY_TOKEN_AGENT_MISMATCH",
            "reason": "capability token target_agent does not match agent_id",
            "path": _norm(token_path),
        }
    if str(token.get("runtime_owner") or "").strip() != runtime_owner:
        return {
            "status": "blocked",
            "blocking_code": "BLOCKED_CAPABILITY_TOKEN_OWNER_MISMATCH",
            "reason": "capability token runtime_owner does not match runtime owner",
            "path": _norm(token_path),
        }
    allowed_actions = [str(item).strip() for item in (token.get("allowed_actions") or []) if str(item).strip()]
    if action not in allowed_actions:
        return {
            "status": "blocked",
            "blocking_code": "BLOCKED_CAPABILITY_TOKEN_ACTION_MISMATCH",
            "reason": "capability token does not allow the requested action",
            "path": _norm(token_path),
        }
    allowed_paths = [str(item).strip() for item in (token.get("allowed_paths") or []) if str(item).strip()]
    if target_path and allowed_paths and not _allowed_path_match(target_path, allowed_paths):
        return {
            "status": "blocked",
            "blocking_code": "BLOCKED_CAPABILITY_TOKEN_PATH_MISMATCH",
            "reason": "capability token does not allow the requested path",
            "path": _norm(token_path),
        }
    return {
        "status": "passed",
        "token_id": str(token.get("token_id") or "").strip(),
        "path": _norm(token_path),
        "allowed_actions": allowed_actions,
        "allowed_paths": allowed_paths,
    }


def run_preflight(root: Path, *, case_root: Path | None = None) -> dict[str, Any]:
    binding_findings = validate_binding(root)
    tool_contract_findings = _flatten_tool_contract_findings(root)
    blockers: list[dict[str, Any]] = []
    if binding_findings or tool_contract_findings:
        blockers.append(
            {
                "code": "BLOCKED_BINDING_NOT_READY",
                "reason": "binding validation and runtime tool contract must pass before debugger can enter harness flow",
                "refs": (binding_findings + tool_contract_findings)[:20],
            }
        )
    payload = _guard_payload(
        stage="preflight",
        status="passed" if not blockers else "blocked",
        blockers=blockers,
        paths={"root": _norm(root), **({"case_root": _norm(case_root)} if case_root else {})},
        extra={
            "checks": {
                "binding_validation": "passed" if not binding_findings else "failed",
                "runtime_tool_contract": "passed" if not tool_contract_findings else "failed",
            }
        },
    )
    if case_root:
        artifact_path = case_root / "artifacts" / "preflight.yaml"
        _dump_yaml(artifact_path, payload)
    return payload


def run_entry_gate(
    root: Path,
    case_root: Path,
    *,
    platform: str,
    entry_mode: str,
    backend: str,
    capture_paths: list[str] | None = None,
    mcp_configured: bool = False,
    remote_transport: str = "",
    single_agent_requested: bool = False,
) -> dict[str, Any]:
    return shared_run_entry_gate(
        root,
        case_root.resolve(),
        platform=platform,
        entry_mode=entry_mode,
        backend=backend,
        capture_paths=capture_paths,
        mcp_configured=mcp_configured,
        remote_transport=remote_transport,
        single_agent_requested=single_agent_requested,
    )


def run_accept_intake(
    root: Path,
    case_root: Path,
    *,
    platform: str,
    entry_mode: str,
    backend: str,
    capture_paths: list[str],
    case_id: str = "",
    run_id: str = "",
    session_id: str = "",
    mcp_configured: bool = False,
    remote_transport: str = "",
    single_agent_requested: bool = False,
    user_goal: str = "",
    symptom_summary: str = "",
) -> dict[str, Any]:
    case_root = case_root.resolve()
    capture_paths = [str(item or "").strip() for item in (capture_paths or []) if str(item or "").strip()]
    entry_payload = run_entry_gate(
        root,
        case_root,
        platform=platform,
        entry_mode=entry_mode,
        backend=backend,
        capture_paths=capture_paths,
        mcp_configured=mcp_configured,
        remote_transport=remote_transport,
        single_agent_requested=single_agent_requested,
    )
    if entry_payload["status"] != "passed":
        return _guard_payload(
            stage="accept_intake",
            status="blocked",
            blockers=list(entry_payload.get("blockers") or []),
            paths={"case_root": _norm(case_root), "entry_gate": _norm(case_root / "artifacts" / "entry_gate.yaml")},
            extra={"entry_gate_status": str(entry_payload.get("status") or "")},
        )

    case_id = _resolve_case_id(case_root, case_id)
    run_id = str(run_id or "").strip() or _next_run_id(case_root)
    run_root = case_root / "runs" / run_id
    if (run_root / "run.yaml").is_file():
        return _guard_payload(
            stage="accept_intake",
            status="blocked",
            blockers=[
                {
                    "code": "BLOCKED_RUN_ALREADY_INITIALIZED",
                    "reason": "run_root already contains run.yaml; accept_intake must remain a single bootstrap transaction",
                    "refs": [_norm(run_root)],
                }
            ],
            paths={"run_root": _norm(run_root)},
        )

    session_id = _resolve_session_id(case_id, run_id, session_id)
    user_goal = str(user_goal or "").strip() or "locate the rendering root cause"
    symptom_summary = str(symptom_summary or "").strip() or "user supplied debugger capture"

    capture_entries, capture_refs, capture_roles = _capture_tokens(case_root, capture_paths)
    session_mode, reference_contract = _default_reference_contract(capture_roles)
    references_manifest = _default_reference_manifest(reference_contract)

    case_yaml = {"case_id": case_id, "current_run": run_id}
    case_input = {
        "schema_version": "1",
        "case_id": case_id,
        "session": {"mode": session_mode, "goal": user_goal},
        "symptom": {"summary": symptom_summary},
        "captures": [
            {
                "capture_id": item["capture_id"],
                "role": item["capture_role"],
                "file_name": item["file_name"],
                "source": item["source"],
                "provenance": {"source_path": item["source_path"]},
            }
            for item in capture_entries
        ],
        "environment": {"api": "unknown"},
        "reference_contract": reference_contract,
        "hints": {},
        "project": {"engine": "unknown"},
    }
    run_yaml = {
        "run_id": run_id,
        "session_id": session_id,
        "platform": platform,
        "coordination_mode": str((entry_payload.get("platform_contract") or {}).get("coordination_mode") or "staged_handoff"),
        "runtime": {
            "coordination_mode": str((entry_payload.get("platform_contract") or {}).get("coordination_mode") or "staged_handoff"),
            "orchestration_mode": str(entry_payload.get("orchestration_mode") or "multi_agent"),
            "single_agent_reason": str(entry_payload.get("single_agent_reason") or ""),
            "backend": backend,
            "entry_mode": entry_mode,
            "context_id": "ctx-orchestrator",
            "runtime_owner": "rdc-debugger",
            "session_id": session_id,
            "workflow_stage": "accepted_intake_initialized",
        },
    }
    hypothesis_board = _default_hypothesis_board(session_id, user_goal, symptom_summary)

    _dump_yaml(case_root / "case.yaml", case_yaml)
    _dump_yaml(case_root / "case_input.yaml", case_input)
    _dump_yaml(case_root / "inputs" / "captures" / "manifest.yaml", {"captures": capture_entries})
    _dump_yaml(case_root / "inputs" / "references" / "manifest.yaml", references_manifest)
    _dump_yaml(run_root / "run.yaml", run_yaml)
    _dump_yaml(run_root / "capture_refs.yaml", {"captures": capture_refs})
    _dump_yaml(run_root / "notes" / "hypothesis_board.yaml", hypothesis_board)
    session_marker = root / "common" / "knowledge" / "library" / "sessions" / ".current_session"
    session_marker.parent.mkdir(parents=True, exist_ok=True)
    session_marker.write_text(f"{session_id}\n", encoding="utf-8")

    intake_payload = run_intake_gate(root, run_root)
    topology_payload = run_runtime_topology(root, run_root, platform=platform)
    blockers: list[dict[str, Any]] = []
    if intake_payload["status"] != "passed":
        blockers.append(
            {
                "code": "BLOCKED_INTAKE_GATE_REQUIRED",
                "reason": "accepted intake did not satisfy the run-level intake gate",
                "refs": [_norm(run_root / "artifacts" / "intake_gate.yaml")],
            }
        )
    if topology_payload["status"] != "passed":
        blockers.append(
            {
                "code": "BLOCKED_RUNTIME_TOPOLOGY_REQUIRED",
                "reason": "accepted intake did not satisfy runtime topology generation",
                "refs": [_norm(run_root / "artifacts" / "runtime_topology.yaml")],
            }
        )
    payload = _guard_payload(
        stage="accept_intake",
        status="passed" if not blockers else "blocked",
        blockers=blockers,
        paths={
            "case_root": _norm(case_root),
            "run_root": _norm(run_root),
            "entry_gate": _norm(case_root / "artifacts" / "entry_gate.yaml"),
            "intake_gate": _norm(run_root / "artifacts" / "intake_gate.yaml"),
            "runtime_topology": _norm(run_root / "artifacts" / "runtime_topology.yaml"),
        },
        extra={
            "case_id": case_id,
            "run_id": run_id,
            "session_id": session_id,
            "entry_gate_status": str(entry_payload.get("status") or ""),
            "intake_gate_status": str(intake_payload.get("status") or ""),
            "runtime_topology_status": str(topology_payload.get("status") or ""),
        },
    )
    _write_guard_artifact(run_root, "accept_intake.yaml", payload)
    return payload


def run_intake_gate(root: Path, run_root: Path) -> dict[str, Any]:
    return shared_run_intake_gate(root, run_root.resolve())


def run_runtime_topology(root: Path, run_root: Path, *, platform: str) -> dict[str, Any]:
    run_root = run_root.resolve()
    payload = shared_run_runtime_topology(root, run_root, platform=platform)
    if not _status_ok(str(payload.get("status") or "")):
        _emit_quality_check(
            root,
            run_root,
            stage="runtime-topology",
            payload=_guard_payload(
                stage="runtime_topology",
                status="blocked",
                blockers=[
                    {
                        "code": "BLOCKED_RUNTIME_TOPOLOGY_FAILED",
                        "reason": "shared runtime_topology failed",
                        "refs": [
                            str(item.get("id") or "").strip()
                            for item in payload.get("checks", [])
                            if item.get("result") != "pass" and str(item.get("id") or "").strip()
                        ][:12],
                    }
                ],
                paths={"runtime_topology": _norm(run_root / "artifacts" / "runtime_topology.yaml")},
            ),
            artifact_path=run_root / "artifacts" / "runtime_topology.yaml",
        )
    return payload


def run_dispatch_readiness(root: Path, run_root: Path, *, platform: str) -> dict[str, Any]:
    run_root = run_root.resolve()
    case_root = run_root.parent.parent
    entry_gate_path = case_root / "artifacts" / "entry_gate.yaml"
    intake_gate_path = run_root / "artifacts" / "intake_gate.yaml"
    topology_path = run_root / "artifacts" / "runtime_topology.yaml"
    hypothesis_board_path = run_root / "notes" / "hypothesis_board.yaml"

    entry_gate = _read_yaml(entry_gate_path) if entry_gate_path.is_file() else {}
    intake_gate = _read_yaml(intake_gate_path) if intake_gate_path.is_file() else {}
    runtime_topology = _read_yaml(topology_path) if topology_path.is_file() else {}
    hypothesis_board = _read_yaml(hypothesis_board_path) if hypothesis_board_path.is_file() else {}
    entry_gate = entry_gate if isinstance(entry_gate, dict) else {}
    intake_gate = intake_gate if isinstance(intake_gate, dict) else {}
    runtime_topology = runtime_topology if isinstance(runtime_topology, dict) else {}
    hypothesis_board = hypothesis_board if isinstance(hypothesis_board, dict) else {}

    blockers: list[dict[str, Any]] = []
    refs: list[str] = []

    if str(entry_gate.get("status") or "").strip() != "passed":
        blockers.append(
            {
                "code": "BLOCKED_REQUIRED_ARTIFACT_MISSING",
                "reason": "artifacts/entry_gate.yaml must exist and be passed before specialist dispatch",
                "refs": [_norm(entry_gate_path)],
            }
        )
    recomputed_intake = build_intake_gate_payload(root, run_root)
    intake_failures = [item for item in recomputed_intake.get("checks", []) if item.get("result") != "pass"]
    if str(intake_gate.get("status") or "").strip() != "passed" or intake_failures:
        blockers.append(
            {
                "code": "BLOCKED_INTAKE_GATE_REQUIRED",
                "reason": "artifacts/intake_gate.yaml must exist, be passed, and stay valid before specialist dispatch or live analysis",
                "refs": [
                    _norm(intake_gate_path),
                    *[str(item.get("id") or "").strip() for item in intake_failures if str(item.get("id") or "").strip()],
                ][:12],
            }
        )
    recomputed_topology = build_runtime_topology_payload(root, run_root, platform=platform)
    topology_failures = [item for item in recomputed_topology.get("checks", []) if item.get("result") != "pass"]
    if str(runtime_topology.get("status") or "").strip() != "passed" or topology_failures:
        blockers.append(
            {
                "code": "BLOCKED_RUNTIME_TOPOLOGY_REQUIRED",
                "reason": "artifacts/runtime_topology.yaml must exist, be passed, and stay valid before staged handoff",
                "refs": [
                    _norm(topology_path),
                    *[str(item.get("id") or "").strip() for item in topology_failures if str(item.get("id") or "").strip()],
                ][:12],
            }
        )
    board_issues = validate_hypothesis_board(hypothesis_board) if hypothesis_board else ["hypothesis_board missing"]
    if board_issues:
        blockers.append(
            {
                "code": "BLOCKED_REQUIRED_ARTIFACT_MISSING",
                "reason": "notes/hypothesis_board.yaml must exist and satisfy the shared schema before staged handoff",
                "refs": [_norm(hypothesis_board_path), *board_issues[:8]],
            }
        )
    orchestration_mode = str(
        runtime_topology.get("orchestration_mode")
        or recomputed_topology.get("orchestration_mode")
        or ""
    ).strip()
    if orchestration_mode == "single_agent_by_user":
        blockers.append(
            {
                "code": "BLOCKED_SINGLE_AGENT_MODE_NO_DISPATCH",
                "reason": "single_agent_by_user runs must not dispatch specialists",
            }
        )

    events = _action_chain_events(root, run_root)
    overreach = workflow_stage_overreach_issues(
        events,
        coordination_mode=str(recomputed_topology.get("coordination_mode") or runtime_topology.get("coordination_mode") or "staged_handoff"),
    )
    refs.extend(overreach)
    status = "passed"
    if overreach:
        status = "blocked"
        blockers = [
            {
                "code": "PROCESS_DEVIATION_MAIN_AGENT_OVERREACH",
                "reason": "rdc-debugger attempted live investigation while waiting_for_specialist_brief",
                "refs": overreach[:8],
            }
        ]
    elif blockers:
        status = "blocked"

    payload = _guard_payload(
        stage="dispatch_readiness",
        status=status,
        blockers=blockers,
        refs=refs[:12] or None,
        paths={
            "run_root": _norm(run_root),
            "entry_gate": _norm(entry_gate_path),
            "intake_gate": _norm(intake_gate_path),
            "runtime_topology": _norm(topology_path),
            "hypothesis_board": _norm(hypothesis_board_path),
            "action_chain": _norm(_action_chain_path(root, run_root)),
        },
        extra={
            "orchestration_mode": orchestration_mode,
            "recomputed_intake_status": str(recomputed_intake.get("status") or ""),
            "recomputed_runtime_topology_status": str(recomputed_topology.get("status") or ""),
        },
    )
    artifact_path = _write_guard_artifact(run_root, "dispatch_readiness.yaml", payload)
    if overreach:
        _emit_process_deviation(
            root,
            run_root,
            deviation_code="PROCESS_DEVIATION_MAIN_AGENT_OVERREACH",
            summary="rdc-debugger attempted live investigation during waiting_for_specialist_brief",
            refs=overreach[:8],
            artifact_path=artifact_path,
        )
    elif blockers:
        _emit_quality_check(root, run_root, stage="dispatch-readiness", payload=payload, artifact_path=artifact_path)
    return payload


def run_dispatch_specialist(
    root: Path,
    run_root: Path,
    *,
    platform: str,
    target_agent: str,
    objective: str,
    ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
) -> dict[str, Any]:
    run_root = run_root.resolve()
    readiness = run_dispatch_readiness(root, run_root, platform=platform)
    if readiness["status"] != "passed":
        return readiness
    if target_agent not in SPECIALIST_TOKEN_AGENTS:
        payload = _guard_payload(
            stage="dispatch_specialist",
            status="blocked",
            blockers=[
                {
                    "code": "BLOCKED_UNKNOWN_SPECIALIST",
                    "reason": "dispatch target must be a known specialist, skeptic, or curator agent",
                    "refs": [target_agent],
                }
            ],
            paths={"run_root": _norm(run_root)},
        )
        _write_guard_artifact(run_root, "dispatch_specialist.yaml", payload)
        return payload

    note_name = NOTE_FILE_BY_AGENT.get(target_agent, f"{target_agent}.md")
    allowed_note_path = _norm(run_root / "notes" / note_name)
    token = issue_capability_token(
        run_root,
        target_agent=target_agent,
        runtime_owner=target_agent,
        allowed_actions=list(DEFAULT_TOKEN_ACTIONS),
        allowed_paths=[allowed_note_path],
        ttl_seconds=ttl_seconds,
    )
    action_chain = _action_chain_path(root, run_root)
    runtime = _runtime_fields(run_root)
    dispatch_event_id = f"evt-dispatch-{_sanitize_token(target_agent)}-{_now_ms()}"
    _append_event(
        action_chain,
        {
            "schema_version": ACTION_CHAIN_SCHEMA,
            "event_id": dispatch_event_id,
            "ts_ms": _now_ms(),
            "run_id": _run_id(run_root),
            "session_id": _extract_session_id(root, run_root),
            "agent_id": "rdc-debugger",
            "event_type": "dispatch",
            "status": "sent",
            "duration_ms": 0,
            "refs": [],
            "payload": {
                **runtime,
                "target_agent": target_agent,
                "objective": objective,
                "capability_token_ref": token["path"],
                "delegation_status": "native_dispatch",
                "fallback_execution_mode": "wrapper",
                "degraded_reasons": [],
            },
        },
    )
    _append_event(
        action_chain,
        {
            "schema_version": ACTION_CHAIN_SCHEMA,
            "event_id": f"evt-stage-waiting-{_sanitize_token(target_agent)}-{_now_ms()}",
            "ts_ms": _now_ms(),
            "run_id": _run_id(run_root),
            "session_id": _extract_session_id(root, run_root),
            "agent_id": "rdc-debugger",
            "event_type": "workflow_stage_transition",
            "status": "entered",
            "duration_ms": 0,
            "refs": [dispatch_event_id],
            "payload": {
                "workflow_stage": "waiting_for_specialist_brief",
                "blocking_code": "",
                "blocking_codes": [],
                "required_artifacts_before_transition": [f"notes/{note_name}"],
            },
        },
    )
    payload = _guard_payload(
        stage="dispatch_specialist",
        status="passed",
        blockers=[],
        paths={
            "run_root": _norm(run_root),
            "action_chain": _norm(action_chain),
            "capability_token": token["path"],
        },
        extra={
            "target_agent": target_agent,
            "objective": objective,
            "capability_token": token,
        },
    )
    _write_guard_artifact(run_root, "dispatch_specialist.yaml", payload)
    return payload


def run_specialist_feedback(
    root: Path,
    run_root: Path,
    *,
    timeout_seconds: int = 300,
    now_ms: int | None = None,
) -> dict[str, Any]:
    run_root = run_root.resolve()
    topology_path = run_root / "artifacts" / "runtime_topology.yaml"
    runtime_topology = _read_yaml(topology_path) if topology_path.is_file() else {}
    runtime_topology = runtime_topology if isinstance(runtime_topology, dict) else {}
    blockers: list[dict[str, Any]] = []

    if str(runtime_topology.get("status") or "").strip() != "passed":
        blockers.append(
            {
                "code": "BLOCKED_RUNTIME_TOPOLOGY_REQUIRED",
                "reason": "specialist feedback guard requires a passed artifacts/runtime_topology.yaml",
                "refs": [_norm(topology_path)],
            }
        )

    events = _action_chain_events(root, run_root)
    now_value = int(now_ms if now_ms is not None else _now_ms())
    timeout_ms = int(timeout_seconds) * 1000
    pending: list[dict[str, Any]] = []

    for event in events:
        if str(event.get("agent_id") or "").strip() != "rdc-debugger":
            continue
        if str(event.get("event_type") or "").strip() != "dispatch":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        target_agent = str(payload.get("target_agent") or "").strip()
        if target_agent not in ACTION_SPECIALISTS:
            continue
        dispatch_ts = int(event.get("ts_ms") or 0)
        feedback = next(
            (
                candidate
                for candidate in events
                if int(candidate.get("ts_ms") or 0) >= dispatch_ts
                and str(candidate.get("agent_id") or "").strip() == target_agent
                and (
                    (
                        str(candidate.get("event_type") or "").strip() == "artifact_write"
                        and specialist_handoff_path_ok(str(((candidate.get("payload") or {}).get("path") or "")), run_root)
                    )
                    or str(candidate.get("event_type") or "").strip() in DISPATCH_FEEDBACK_EVENT_TYPES - {"artifact_write"}
                )
            ),
            None,
        )
        if feedback is not None:
            continue
        age_ms = now_value - dispatch_ts
        if age_ms > timeout_ms:
            pending.append(
                {
                    "target_agent": target_agent,
                    "dispatch_event_id": str(event.get("event_id") or "").strip() or "?",
                    "dispatch_ts_ms": dispatch_ts,
                    "age_ms": age_ms,
                }
            )

    if pending:
        blockers.append(
            {
                "code": "BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT",
                "reason": "a dispatched specialist exceeded the feedback budget without writing a handoff artifact or review event",
                "refs": [
                    f"{item['target_agent']}@{item['dispatch_event_id']} age_ms={item['age_ms']}"
                    for item in pending[:8]
                ],
            }
        )

    payload = _guard_payload(
        stage="specialist_feedback",
        status="passed" if not blockers else "blocked",
        blockers=blockers,
        paths={
            "run_root": _norm(run_root),
            "runtime_topology": _norm(topology_path),
            "action_chain": _norm(_action_chain_path(root, run_root)),
        },
        extra={
            "timeout_seconds": int(timeout_seconds),
            "now_ms": now_value,
            "pending_dispatches": pending,
        },
    )
    artifact_path = _write_guard_artifact(run_root, "specialist_feedback.yaml", payload)
    if blockers:
        _emit_quality_check(root, run_root, stage="specialist-feedback", payload=payload, artifact_path=artifact_path)
    return payload


def run_final_audit(root: Path, run_root: Path, *, platform: str) -> dict[str, Any]:
    return write_run_audit_artifact(root, run_root.resolve(), platform)


def run_render_user_verdict(root: Path, run_root: Path) -> dict[str, Any]:
    run_root = run_root.resolve()
    compliance_path = run_root / "artifacts" / "run_compliance.yaml"
    report_md = run_root / "reports" / "report.md"
    visual_report = run_root / "reports" / "visual_report.html"
    fix_verification = run_root / "artifacts" / "fix_verification.yaml"

    blockers: list[dict[str, Any]] = []
    compliance = _read_yaml(compliance_path) if compliance_path.is_file() else {}
    if not compliance_path.is_file():
        blockers.append(
            {
                "code": "BLOCKED_RUN_COMPLIANCE_REQUIRED",
                "reason": "render_user_verdict requires artifacts/run_compliance.yaml",
                "refs": [_norm(compliance_path)],
            }
        )
    elif str((compliance or {}).get("status") or "").strip() != "passed":
        failing = [
            str(item.get("id") or "").strip()
            for item in ((compliance or {}).get("checks") or [])
            if isinstance(item, dict) and str(item.get("result") or "").strip() == "fail"
        ]
        blockers.append(
            {
                "code": "BLOCKED_RUN_COMPLIANCE_NOT_PASSED",
                "reason": "render_user_verdict requires run_compliance.yaml status=passed",
                "refs": failing[:12] or [_norm(compliance_path)],
            }
        )
    for path, code in (
        (report_md, "BLOCKED_REPORT_MISSING"),
        (visual_report, "BLOCKED_REPORT_MISSING"),
        (fix_verification, "BLOCKED_FIX_VERIFICATION_MISSING"),
    ):
        if not path.is_file():
            blockers.append({"code": code, "reason": f"missing required artifact: {_norm(path)}", "refs": [_norm(path)]})
    if blockers:
        return _guard_payload(
            stage="user_verdict",
            status="blocked",
            blockers=blockers,
            paths={"run_root": _norm(run_root), "run_compliance": _norm(compliance_path)},
        )

    fix_data = _read_yaml(fix_verification)
    if not isinstance(fix_data, dict):
        fix_data = {}
    verdict = str(fix_data.get("verdict") or (fix_data.get("overall_result") or {}).get("verdict") or "").strip()
    overall_status = str((fix_data.get("overall_result") or {}).get("status") or "").strip()
    response_lines = [
        "当前 run 已完成 debugger 流程。",
        "",
        f"- 修复判断：{verdict or 'unknown'}",
        f"- verification_status：{overall_status or 'unknown'}",
        f"- 报告产物：{_norm(report_md.relative_to(run_root))}, {_norm(visual_report.relative_to(run_root))}",
        f"- 合规审计：{_norm(compliance_path.relative_to(run_root))} = passed",
    ]
    payload = {
        "schema_version": GUARD_SCHEMA,
        "generated_by": "harness_guard",
        "generated_at": _now_iso(),
        "guard_stage": "user_verdict",
        "status": "passed",
        "run_id": _run_id(run_root),
        "session_id": _extract_session_id(root, run_root),
        "verdict": verdict,
        "verification_status": overall_status,
        "response_lines": response_lines,
        "paths": {
            "report_md": _norm(report_md),
            "visual_report_html": _norm(visual_report),
            "run_compliance": _norm(compliance_path),
            "fix_verification": _norm(fix_verification),
        },
    }
    _write_guard_artifact(run_root, "user_verdict.yaml", payload)
    return payload


def _print_yaml(payload: dict[str, Any]) -> None:
    print(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), end="")


def main() -> int:
    parser = argparse.ArgumentParser(description="Shared cross-platform harness guard")
    parser.add_argument("--root", type=Path, default=None, help="debugger root override")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="run binding and runtime tool contract preflight")
    preflight.add_argument("--case-root", type=Path, default=None, help="optional workspace case root for artifact output")

    entry = subparsers.add_parser("entry-gate", help="run shared entry gate")
    entry.add_argument("--case-root", type=Path, required=True)
    entry.add_argument("--platform", required=True)
    entry.add_argument("--entry-mode", required=True, choices=("cli", "mcp"))
    entry.add_argument("--backend", required=True, choices=("local", "remote"))
    entry.add_argument("--capture-path", action="append", default=[])
    entry.add_argument("--mcp-configured", action="store_true")
    entry.add_argument("--remote-transport", default="")
    entry.add_argument("--single-agent-by-user", action="store_true")

    accept = subparsers.add_parser("accept-intake", help="initialize case/run and run intake/topology as a single transaction")
    accept.add_argument("--case-root", type=Path, required=True)
    accept.add_argument("--platform", required=True)
    accept.add_argument("--entry-mode", required=True, choices=("cli", "mcp"))
    accept.add_argument("--backend", required=True, choices=("local", "remote"))
    accept.add_argument("--capture-path", action="append", default=[])
    accept.add_argument("--case-id", default="")
    accept.add_argument("--run-id", default="")
    accept.add_argument("--session-id", default="")
    accept.add_argument("--mcp-configured", action="store_true")
    accept.add_argument("--remote-transport", default="")
    accept.add_argument("--single-agent-by-user", action="store_true")
    accept.add_argument("--user-goal", default="")
    accept.add_argument("--symptom-summary", default="")

    intake = subparsers.add_parser("intake-gate", help="run shared intake gate")
    intake.add_argument("--run-root", type=Path, required=True)

    dispatch_ready = subparsers.add_parser("dispatch-readiness", help="validate specialist dispatch preconditions")
    dispatch_ready.add_argument("--run-root", type=Path, required=True)
    dispatch_ready.add_argument("--platform", required=True)

    dispatch = subparsers.add_parser("dispatch-specialist", help="issue a specialist capability token and append dispatch event")
    dispatch.add_argument("--run-root", type=Path, required=True)
    dispatch.add_argument("--platform", required=True)
    dispatch.add_argument("--target-agent", required=True)
    dispatch.add_argument("--objective", required=True)
    dispatch.add_argument("--ttl-seconds", type=int, default=DEFAULT_TOKEN_TTL_SECONDS)

    feedback = subparsers.add_parser("specialist-feedback", help="check for specialist feedback timeout")
    feedback.add_argument("--run-root", type=Path, required=True)
    feedback.add_argument("--timeout-seconds", type=int, default=300)
    feedback.add_argument("--now-ms", type=int, default=None)

    topology = subparsers.add_parser("runtime-topology", help="run shared runtime topology builder")
    topology.add_argument("--run-root", type=Path, required=True)
    topology.add_argument("--platform", required=True)

    final = subparsers.add_parser("final-audit", help="run shared final compliance audit")
    final.add_argument("--run-root", type=Path, required=True)
    final.add_argument("--platform", required=True)

    verdict = subparsers.add_parser("render-user-verdict", help="render a deterministic user verdict from final artifacts")
    verdict.add_argument("--run-root", type=Path, required=True)

    args = parser.parse_args()
    root = _debugger_root(args.root)

    try:
        if args.command == "preflight":
            payload = run_preflight(root, case_root=args.case_root.resolve() if args.case_root else None)
        elif args.command == "entry-gate":
            payload = run_entry_gate(
                root,
                args.case_root.resolve(),
                platform=str(args.platform or "").strip(),
                entry_mode=args.entry_mode,
                backend=args.backend,
                capture_paths=list(args.capture_path or []),
                mcp_configured=bool(args.mcp_configured),
                remote_transport=str(args.remote_transport or "").strip(),
                single_agent_requested=bool(args.single_agent_by_user),
            )
        elif args.command == "accept-intake":
            payload = run_accept_intake(
                root,
                args.case_root.resolve(),
                platform=str(args.platform or "").strip(),
                entry_mode=args.entry_mode,
                backend=args.backend,
                capture_paths=list(args.capture_path or []),
                case_id=str(args.case_id or "").strip(),
                run_id=str(args.run_id or "").strip(),
                session_id=str(args.session_id or "").strip(),
                mcp_configured=bool(args.mcp_configured),
                remote_transport=str(args.remote_transport or "").strip(),
                single_agent_requested=bool(args.single_agent_by_user),
                user_goal=str(args.user_goal or "").strip(),
                symptom_summary=str(args.symptom_summary or "").strip(),
            )
        elif args.command == "intake-gate":
            payload = run_intake_gate(root, args.run_root.resolve())
        elif args.command == "dispatch-readiness":
            payload = run_dispatch_readiness(root, args.run_root.resolve(), platform=str(args.platform or "").strip())
        elif args.command == "dispatch-specialist":
            payload = run_dispatch_specialist(
                root,
                args.run_root.resolve(),
                platform=str(args.platform or "").strip(),
                target_agent=str(args.target_agent or "").strip(),
                objective=str(args.objective or "").strip(),
                ttl_seconds=int(args.ttl_seconds),
            )
        elif args.command == "specialist-feedback":
            payload = run_specialist_feedback(
                root,
                args.run_root.resolve(),
                timeout_seconds=int(args.timeout_seconds),
                now_ms=args.now_ms,
            )
        elif args.command == "runtime-topology":
            payload = run_runtime_topology(root, args.run_root.resolve(), platform=str(args.platform or "").strip())
        elif args.command == "final-audit":
            payload = run_final_audit(root, args.run_root.resolve(), platform=str(args.platform or "").strip())
        elif args.command == "render-user-verdict":
            payload = run_render_user_verdict(root, args.run_root.resolve())
        else:  # pragma: no cover
            raise ValueError(f"unknown command: {args.command}")
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 2

    _print_yaml(payload)
    if not _status_ok(str(payload.get("status") or "")):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
