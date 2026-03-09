#!/usr/bin/env python3
"""Audit whether a debugger run complies with the framework contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import yaml
except ModuleNotFoundError:
    req = Path(__file__).resolve().parents[1] / "requirements.txt"
    print("missing dependency 'PyYAML'", file=sys.stderr)
    print(f"install with: python -m pip install -r {req}", file=sys.stderr)
    raise SystemExit(2)


ACTION_SPECIALISTS = {
    "triage_agent",
    "capture_repro_agent",
    "pass_graph_pipeline_agent",
    "pixel_forensics_agent",
    "shader_ir_agent",
    "driver_device_agent",
}

FINAL_REPORT_NAMES = ("report.md", "visual_report.html")
EVENT_RE = re.compile(r"\bevent[_\s:=#-]*(\d+)\b", re.IGNORECASE)
SESSION_RE = re.compile(r"\bsession_id\s*[:=]\s*([A-Za-z0-9._-]+)")
CAPTURE_FILE_RE = re.compile(r"\bcapture_file_id\s*[:=]\s*([A-Za-z0-9._-]+)")
FINAL_VERDICT_RE = re.compile(r"DEBUGGER_FINAL_VERDICT|final verdict|最终裁决|结案", re.IGNORECASE)


def _debugger_root(default: Path | None = None) -> Path:
    return default.resolve() if default else Path(__file__).resolve().parents[3]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="ignore")


def _normalize_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_framework_compliance(root: Path) -> dict[str, Any]:
    path = root / "common" / "config" / "framework_compliance.json"
    return _read_json(path)


def _load_platform_caps(root: Path) -> dict[str, Any]:
    return _read_json(root / "common" / "config" / "platform_capabilities.json")


def _default_platform(root: Path, requested: str | None) -> str:
    if requested:
        return requested
    return root.name


def _infer_run_root(root: Path) -> Path:
    workspace = root / "workspace" / "cases"
    candidates: list[Path] = []
    if workspace.is_dir():
        for run_dir in workspace.glob("*/runs/*"):
            if run_dir.is_dir():
                candidates.append(run_dir)
    if not candidates:
        raise FileNotFoundError("no run directories found under workspace/cases")
    candidates.sort(
        key=lambda p: max((child.stat().st_mtime for child in p.rglob("*")), default=p.stat().st_mtime),
        reverse=True,
    )
    return candidates[0]


def _load_action_chain(path: Path) -> list[dict[str, Any]]:
    lines = [line.strip() for line in _load_text(path).splitlines() if line.strip()]
    if not lines:
        return []
    if len(lines) == 1 and lines[0].startswith("{"):
        payload = json.loads(lines[0])
        if isinstance(payload, dict) and isinstance(payload.get("steps"), list):
            return [step for step in payload["steps"] if isinstance(step, dict)]
    rows: list[dict[str, Any]] = []
    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _extract_session_id(run_data: dict[str, Any], session_marker: Path) -> str | None:
    candidates = [
        run_data.get("session_id"),
        (run_data.get("debug") or {}).get("session_id") if isinstance(run_data.get("debug"), dict) else None,
        (run_data.get("runtime") or {}).get("session_id") if isinstance(run_data.get("runtime"), dict) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    if session_marker.is_file():
        value = session_marker.read_text(encoding="utf-8").lstrip("\ufeff").strip()
        if value and value != "session-unset":
            return value
    return None


def _extract_matches(text: str, pattern: re.Pattern[str]) -> list[str]:
    return [match.strip() for match in pattern.findall(text or "") if str(match).strip()]


def _contains_dispatch(step: dict[str, Any], formal_entry_role: str) -> bool:
    action_type = str(step.get("action_type", "")).strip()
    message_type = str(step.get("message_type", "")).strip()
    agent = str(step.get("agent", "")).strip()
    if message_type == "TASK_DISPATCH":
        return True
    if action_type == "task_dispatch":
        return True
    if action_type == "message_send" and agent == formal_entry_role and step.get("message_to"):
        return True
    return False


def _contains_specialist_evidence(step: dict[str, Any]) -> bool:
    if str(step.get("agent", "")).strip() not in ACTION_SPECIALISTS:
        return False
    return str(step.get("action_type", "")).strip() in {
        "tool_call",
        "evidence_add",
        "hypothesis_update",
        "message_send",
        "artifact_write",
    }


def _contains_skeptic(step: dict[str, Any]) -> bool:
    if str(step.get("agent", "")).strip() != "skeptic_agent":
        return False
    action_type = str(step.get("action_type", "")).strip()
    message_type = str(step.get("message_type", "")).strip()
    return action_type in {"message_send", "quality_check", "artifact_write"} or message_type.startswith("SKEPTIC_")


def _contains_curator_artifact(step: dict[str, Any]) -> bool:
    if str(step.get("agent", "")).strip() != "curator_agent":
        return False
    if str(step.get("action_type", "")).strip() != "artifact_write":
        return False
    params = step.get("params")
    text = json.dumps(params, ensure_ascii=False) if isinstance(params, dict) else json.dumps(step, ensure_ascii=False)
    return any(name in text for name in ("session_evidence.yaml", "skeptic_signoff.yaml", "action_chain.jsonl"))


def _contains_audit_pass(step: dict[str, Any]) -> bool:
    if str(step.get("action_type", "")).strip() != "quality_check":
        return False
    validator = str(step.get("validator", "")).strip()
    result = str(step.get("result", "")).strip()
    return validator == "run_compliance_audit" and result == "pass"


def _append_audit_entry(path: Path, platform: str, result: str, summary: str) -> None:
    entry = {
        "timestamp": _now_iso(),
        "agent": "team_lead",
        "action_type": "quality_check",
        "validator": "run_compliance_audit",
        "platform": platform,
        "result": result,
        "output_summary": summary,
    }
    serialized = json.dumps(entry, ensure_ascii=False)
    existing = _load_text(path) if path.exists() else ""
    if serialized in existing:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(serialized)
        handle.write("\n")


def _dump_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _check(result: list[dict[str, Any]], check_id: str, passed: bool, detail: str, *, path: Path | None = None, refs: list[str] | None = None) -> None:
    result.append(
        {
            "id": check_id,
            "result": "pass" if passed else "fail",
            "detail": detail,
            **({"path": _normalize_path(path)} if path else {}),
            **({"refs": refs} if refs else {}),
        },
    )


def run_audit(root: Path, run_root: Path, platform: str) -> dict[str, Any]:
    compliance = _load_framework_compliance(root)
    caps = _load_platform_caps(root)
    platform_rules = (compliance.get("platforms") or {}).get(platform)
    platform_caps = (caps.get("platforms") or {}).get(platform)
    if not isinstance(platform_rules, dict):
        raise KeyError(f"unknown platform in framework_compliance.json: {platform}")
    if not isinstance(platform_caps, dict):
        raise KeyError(f"unknown platform in platform_capabilities.json: {platform}")

    checks: list[dict[str, Any]] = []
    contract = compliance["runtime_artifact_contract"]
    formal_entry_role = str(platform_rules.get("formal_entry_role", "team_lead"))
    expected_coordination = str(platform_rules.get("coordination_mode", ""))

    case_root = run_root.parent.parent
    case_yaml = case_root / "case.yaml"
    run_yaml = run_root / "run.yaml"
    hypothesis_board = run_root / "notes" / "hypothesis_board.yaml"
    report_md = run_root / "reports" / "report.md"
    visual_report = run_root / "reports" / "visual_report.html"
    compliance_artifact = run_root / contract["run_compliance_artifact"]
    session_marker = root / "common" / "knowledge" / "library" / "sessions" / ".current_session"

    run_data = _read_yaml(run_yaml) if run_yaml.is_file() else {}
    if not isinstance(run_data, dict):
        run_data = {}
    session_id = _extract_session_id(run_data, session_marker)

    _check(checks, "case_yaml", case_yaml.is_file(), "case.yaml must exist", path=case_yaml)
    _check(checks, "run_yaml", run_yaml.is_file(), "run.yaml must exist", path=run_yaml)
    _check(checks, "hypothesis_board", hypothesis_board.is_file(), "notes/hypothesis_board.yaml must exist", path=hypothesis_board)
    _check(checks, "report_md", report_md.is_file(), "reports/report.md must exist", path=report_md)
    _check(checks, "visual_report_html", visual_report.is_file(), "reports/visual_report.html must exist", path=visual_report)

    run_platform = str(run_data.get("platform", "") or (run_data.get("debug") or {}).get("platform", "")).strip()
    _check(
        checks,
        "platform_match",
        (not run_platform) or (run_platform == platform),
        f"run platform should match requested platform ({platform})",
        path=run_yaml if run_yaml.is_file() else None,
    )

    run_coordination = str(run_data.get("coordination_mode", "") or (run_data.get("runtime") or {}).get("coordination_mode", "")).strip()
    _check(
        checks,
        "coordination_mode",
        run_coordination == expected_coordination,
        f"coordination_mode must be {expected_coordination}",
        path=run_yaml if run_yaml.is_file() else None,
    )

    _check(
        checks,
        "platform_capability_alignment",
        str(platform_caps.get("coordination_mode", "")).strip() == expected_coordination,
        "framework_compliance coordination_mode must match platform_capabilities",
    )

    if session_id:
        session_dir = root / "common" / "knowledge" / "library" / "sessions" / session_id
        session_evidence = session_dir / "session_evidence.yaml"
        skeptic_signoff = session_dir / "skeptic_signoff.yaml"
        action_chain = session_dir / "action_chain.jsonl"
        _check(checks, "session_id", True, f"resolved session_id={session_id}", refs=[session_id])
    else:
        session_dir = root / "common" / "knowledge" / "library" / "sessions"
        session_evidence = session_dir / "session_evidence.yaml"
        skeptic_signoff = session_dir / "skeptic_signoff.yaml"
        action_chain = session_dir / "action_chain.jsonl"
        _check(checks, "session_id", False, "session_id could not be resolved from run.yaml or .current_session", path=run_yaml if run_yaml.is_file() else session_marker)

    evidence_data = _read_yaml(session_evidence) if session_evidence.is_file() else {}
    if not isinstance(evidence_data, dict):
        evidence_data = {}
    skeptic_data = _read_yaml(skeptic_signoff) if skeptic_signoff.is_file() else {}
    action_steps = _load_action_chain(action_chain) if action_chain.is_file() else []

    _check(checks, "session_evidence", session_evidence.is_file(), "session_evidence.yaml must exist", path=session_evidence)
    _check(checks, "skeptic_signoff", skeptic_signoff.is_file(), "skeptic_signoff.yaml must exist", path=skeptic_signoff)
    _check(checks, "action_chain", action_chain.is_file(), "action_chain.jsonl must exist", path=action_chain)

    anchor = evidence_data.get("causal_anchor") if isinstance(evidence_data.get("causal_anchor"), dict) else {}
    anchor_ok = all(str(anchor.get(key, "")).strip() for key in ("type", "ref", "established_by", "justification"))
    _check(checks, "causal_anchor", anchor_ok, "session_evidence must contain a complete causal_anchor", path=session_evidence if session_evidence.is_file() else None)

    evidence_items = evidence_data.get("evidence")
    if not isinstance(evidence_items, list):
        evidence_items = []
    counterfactual_ok = any(
        isinstance(item, dict)
        and item.get("type") == "counterfactual_test"
        and item.get("result") == "passed"
        for item in evidence_items
    )
    _check(checks, "counterfactual", counterfactual_ok, "session_evidence must contain a passed counterfactual_test", path=session_evidence if session_evidence.is_file() else None)

    skeptic_signed = False
    if isinstance(skeptic_data, dict):
        sign_off = skeptic_data.get("sign_off")
        skeptic_signed = isinstance(sign_off, dict) and sign_off.get("signed") is True
    elif isinstance(skeptic_data, list):
        skeptic_signed = any(
            isinstance(item, dict)
            and item.get("message_type") == "SKEPTIC_SIGN_OFF"
            and isinstance(item.get("sign_off"), dict)
            and item["sign_off"].get("signed") is True
            for item in skeptic_data
        )
    _check(checks, "skeptic_signoff_status", skeptic_signed, "skeptic_signoff artifact must contain a signed approval", path=skeptic_signoff if skeptic_signoff.is_file() else None)

    dispatch_ok = any(_contains_dispatch(step, formal_entry_role) for step in action_steps)
    specialist_ok = any(_contains_specialist_evidence(step) for step in action_steps)
    skeptic_ok = any(_contains_skeptic(step) for step in action_steps)
    curator_ok = any(_contains_curator_artifact(step) for step in action_steps)
    workflow_violation = expected_coordination == "workflow_stage" and any(
        str(step.get("agent", "")).strip() in ACTION_SPECIALISTS and str(step.get("action_type", "")).strip() == "message_send"
        for step in action_steps
    )
    _check(checks, "action_chain_dispatch", dispatch_ok, "action_chain must contain a TASK_DISPATCH-equivalent entry from team_lead", path=action_chain if action_chain.is_file() else None)
    _check(checks, "action_chain_specialist", specialist_ok, "action_chain must contain specialist evidence or tool output", path=action_chain if action_chain.is_file() else None)
    _check(checks, "action_chain_skeptic", skeptic_ok, "action_chain must contain skeptic review activity", path=action_chain if action_chain.is_file() else None)
    _check(checks, "action_chain_curator", curator_ok, "action_chain must contain curator artifact writes", path=action_chain if action_chain.is_file() else None)
    _check(checks, "workflow_stage_integrity", not workflow_violation, "workflow_stage platforms must not simulate concurrent specialist handoff", path=action_chain if action_chain.is_file() else None)

    report_text = "\n".join(_load_text(path) for path in (report_md, visual_report) if path.is_file())
    report_session_ids = _extract_matches(report_text, SESSION_RE)
    report_capture_ids = _extract_matches(report_text, CAPTURE_FILE_RE)
    report_events = _extract_matches(report_text, EVENT_RE)
    evidence_text = json.dumps(evidence_data, ensure_ascii=False)
    action_text = "\n".join(json.dumps(step, ensure_ascii=False) for step in action_steps)
    run_text = json.dumps(run_data, ensure_ascii=False)

    session_ref_ok = (not report_session_ids) or (session_id in report_session_ids)
    capture_ref_ok = (not report_capture_ids) or any(token in (run_text + evidence_text + action_text) for token in report_capture_ids)
    event_ref_ok = (not report_events) or all(
        (f"event:{event_id}" in evidence_text) or (f"event {event_id}" in report_text.lower()) or (f'"event_id": {int(event_id)}' in action_text)
        for event_id in report_events
    )
    _check(checks, "report_session_mapping", session_ref_ok, "report session_id references must map to the resolved session artifact", path=report_md if report_md.is_file() else None, refs=report_session_ids or None)
    _check(checks, "report_capture_mapping", capture_ref_ok, "report capture_file_id references must map to run/session evidence", path=report_md if report_md.is_file() else None, refs=report_capture_ids or None)
    _check(checks, "report_event_mapping", event_ref_ok, "report event references must map to session evidence or action chain", path=report_md if report_md.is_file() else None, refs=report_events or None)

    bug_refs = re.findall(r"BUG-[A-Z0-9-]+", report_text, re.IGNORECASE)
    final_verdict_present = bool(FINAL_VERDICT_RE.search(report_text))
    final_ref_ok = bool(bug_refs) or final_verdict_present
    _check(checks, "final_refs", final_ref_ok, "report must reference BugCard/BugFull or include DEBUGGER_FINAL_VERDICT", path=report_md if report_md.is_file() else None, refs=bug_refs or None)

    if platform_rules.get("enforcement_mode") == "audit_only_gate":
        prior_pass = compliance_artifact.is_file() and isinstance(_read_yaml(compliance_artifact), dict) and (_read_yaml(compliance_artifact).get("status") == "passed")
        _check(
            checks,
            "audit_only_gate",
            True,
            "audit-only platforms treat finalization as draft until artifacts/run_compliance.yaml(status=passed) exists",
            path=compliance_artifact,
        )
    else:
        _check(checks, "audit_only_gate", True, "native-hook/workflow platforms do not require a prior run_compliance.yaml before first audit")

    passed = all(item["result"] == "pass" for item in checks if item["id"] != "audit_only_gate")
    status = "passed" if passed else "failed"
    summary = {
        "passed": sum(1 for item in checks if item["result"] == "pass"),
        "failed": sum(1 for item in checks if item["result"] == "fail"),
    }
    return {
        "schema_version": "1",
        "platform": platform,
        "run_root": _normalize_path(run_root),
        "generated_by": "run_compliance_audit",
        "generated_at": _now_iso(),
        "status": status,
        "session_id": session_id or "",
        "checks": checks,
        "summary": summary,
        "paths": {
            "case_yaml": _normalize_path(case_yaml),
            "run_yaml": _normalize_path(run_yaml),
            "hypothesis_board": _normalize_path(hypothesis_board),
            "session_evidence": _normalize_path(session_evidence),
            "skeptic_signoff": _normalize_path(skeptic_signoff),
            "action_chain": _normalize_path(action_chain),
            "report_md": _normalize_path(report_md),
            "visual_report_html": _normalize_path(visual_report),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit debugger run compliance")
    parser.add_argument("--platform", required=False, help="platform key")
    parser.add_argument("--run-root", type=Path, default=None, help="workspace run root")
    parser.add_argument("--root", type=Path, default=None, help="debugger root override")
    parser.add_argument("--strict", action="store_true", help="return non-zero on failure")
    args = parser.parse_args()

    root = _debugger_root(args.root)
    run_root = args.run_root.resolve() if args.run_root else _infer_run_root(root)
    platform = _default_platform(root, args.platform)

    try:
        payload = run_audit(root, run_root, platform)
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 2

    action_chain_path = Path(payload["paths"]["action_chain"])
    _append_audit_entry(
        action_chain_path,
        platform,
        "pass" if payload["status"] == "passed" else "fail",
        f"run compliance audit {payload['status']}",
    )
    artifact_path = run_root / "artifacts" / "run_compliance.yaml"
    _dump_yaml(artifact_path, payload)

    print(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), end="")
    if args.strict and payload["status"] != "passed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
