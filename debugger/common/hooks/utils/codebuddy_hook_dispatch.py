#!/usr/bin/env python3
"""Shared hook dispatcher for native-hook and pseudo-hook platforms.

Modes:
  - session-start
  - pretool-live
  - posttool-artifact
  - write-bugcard
  - write-skeptic
  - stop-gate
  - stop-gate-force
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

KEYWORDS = (
    "DEBUGGER_FINAL_VERDICT",
    "\u6700\u7ec8\u88c1\u51b3",
    "\u6839\u56e0\u786e\u8ba4",
    "\u7ed3\u6848",
    "final verdict",
    "case closed",
)
_SAFE_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PATH_KEYS = ("file_path", "path", "output_file", "output_path", "file")
_NESTED_PATH_KEYS = ("tool_input", "tool_result", "result", "output", "payload")

UTILS_ROOT = Path(__file__).resolve().parent
if str(UTILS_ROOT) not in sys.path:
    sys.path.insert(0, str(UTILS_ROOT))

from harness_guard import run_dispatch_readiness, run_preflight, validate_capability_token  # noqa: E402


def _normalize_path_text(value: str) -> str:
    return str(value or "").strip().replace("\\", "/")


def _is_yaml_path(path: str) -> bool:
    lowered = _normalize_path_text(path).lower()
    return lowered.endswith(".yaml") or lowered.endswith(".yml")


def _is_bugcard_path(path: str) -> bool:
    lowered = _normalize_path_text(path).lower()
    return "/knowledge/library/bugcards/" in lowered and _is_yaml_path(lowered)


def _is_skeptic_signoff_path(path: str) -> bool:
    lowered = _normalize_path_text(path).lower()
    if not _is_yaml_path(lowered):
        return False
    return "/knowledge/library/sessions/" in lowered and (
        lowered.endswith("/skeptic_signoff.yaml") or lowered.endswith("/skeptic_signoff.yml")
    )


def _debug_agent_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def _py_cmd(*parts: str) -> list[str]:
    return [sys.executable, *[str(p) for p in parts]]


def _validator_paths(root: Path) -> tuple[Path, Path, Path, Path]:
    validators = root / "common" / "hooks" / "validators"
    return (
        validators / "bugcard_validator.py",
        validators / "causal_anchor_validator.py",
        validators / "counterfactual_validator.py",
        validators / "skeptic_signoff_checker.py",
    )


def _script_paths(root: Path) -> tuple[Path, Path]:
    resolve_artifact = root / "common" / "hooks" / "utils" / "resolve_session_artifact.py"
    validate_contract = root / "common" / "hooks" / "utils" / "validate_tool_contract_runtime.py"
    return resolve_artifact, validate_contract


def _parse_json_payload(text: str) -> dict[str, Any]:
    payload = str(text or "").strip()
    if not payload:
        return {}
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _find_path_in_payload(payload: Any, *, depth: int = 0) -> str:
    if depth > 4:
        return ""
    if isinstance(payload, str):
        nested = _parse_json_payload(payload)
        if nested:
            return _find_path_in_payload(nested, depth=depth + 1)
    if isinstance(payload, dict):
        for key in _PATH_KEYS:
            candidate = str(payload.get(key, "")).strip()
            if candidate:
                return candidate
        for key in _NESTED_PATH_KEYS:
            nested = payload.get(key)
            candidate = _find_path_in_payload(nested, depth=depth + 1)
            if candidate:
                return candidate
        for value in payload.values():
            candidate = _find_path_in_payload(value, depth=depth + 1)
            if candidate:
                return candidate
    elif isinstance(payload, list):
        for item in payload:
            candidate = _find_path_in_payload(item, depth=depth + 1)
            if candidate:
                return candidate
    return ""


def _extract_tool_name(stdin_text: str = "") -> str:
    payload = _parse_json_payload(stdin_text)
    if not payload:
        return ""
    for key in ("tool_name", "toolName", "tool"):
        value = str(payload.get(key, "")).strip()
        if value:
            return value
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("tool_name", "toolName", "tool"):
            value = str(tool_input.get(key, "")).strip()
            if value:
                return value
    return ""


def _extract_tool_output_file(stdin_text: str = "") -> str:
    env_payload = _parse_json_payload(os.environ.get("CODEBUDDY_TOOL_INPUT", ""))
    for payload in (env_payload, _parse_json_payload(stdin_text)):
        candidate = _find_path_in_payload(payload)
        if candidate:
            return candidate
    return str(os.environ.get("TOOL_OUTPUT_FILE", "")).strip()


def _relay(proc: subprocess.CompletedProcess[str]) -> None:
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)


def _run_root_from_env() -> Path | None:
    value = str(os.environ.get("DEBUGGER_RUN_ROOT", "")).strip()
    return Path(value).resolve() if value else None


def _case_root_from_env() -> Path | None:
    value = str(os.environ.get("DEBUGGER_CASE_ROOT", "")).strip()
    return Path(value).resolve() if value else None


def _validate_session_id(session_id: str) -> str:
    sid = str(session_id or "").strip()
    if not sid:
        raise ValueError("empty session id")
    if sid in {".", ".."}:
        raise ValueError(f"invalid session id: {sid!r}")
    if not _SAFE_SESSION_ID_RE.match(sid):
        raise ValueError(f"invalid session id (must be a single path-safe token): {sid!r}")
    return sid


def _cmd_write_bugcard(root: Path) -> int:
    bugcard_validator, _, _, _ = _validator_paths(root)
    _, _, _, skeptic_checker = _validator_paths(root)
    _, validate_contract = _script_paths(root)
    stdin_text = sys.stdin.read()
    tool_name = _extract_tool_name(stdin_text)
    file_path = _extract_tool_output_file(stdin_text)
    if tool_name and tool_name != "Write":
        return 0
    if not file_path or not _is_bugcard_path(file_path):
        return 0

    strict = _run(_py_cmd(str(validate_contract), "--strict"))
    _relay(strict)
    if strict.returncode != 0:
        return strict.returncode

    proc = _run(_py_cmd(str(bugcard_validator), file_path))
    _relay(proc)
    if proc.returncode != 0:
        return proc.returncode

    # Bind BugCard write to a real Skeptic BugCard signoff under current session.
    current = root / "common" / "knowledge" / "library" / "sessions" / ".current_session"
    if not current.is_file():
        print(f"missing session marker: {current}", file=sys.stderr)
        return 1
    session_id = current.read_text(encoding="utf-8").lstrip("\ufeff").strip()
    if (not session_id) or (session_id == "session-unset"):
        print(f"invalid current session id: {session_id!r} ({current})", file=sys.stderr)
        return 1
    try:
        safe_session_id = _validate_session_id(session_id)
    except ValueError as exc:
        print(f"invalid current session id: {exc} ({current})", file=sys.stderr)
        return 1

    signoff_path = root / "common" / "knowledge" / "library" / "sessions" / safe_session_id / "skeptic_signoff.yaml"
    if not signoff_path.is_file():
        print(f"missing skeptic signoff artifact: {signoff_path}", file=sys.stderr)
        return 1

    proc2 = _run(_py_cmd(str(skeptic_checker), str(signoff_path), "--mode", "bugcard"))
    _relay(proc2)
    return proc2.returncode


def _cmd_write_skeptic(root: Path) -> int:
    _, _, _, skeptic_checker = _validator_paths(root)
    _, validate_contract = _script_paths(root)
    stdin_text = sys.stdin.read()
    tool_name = _extract_tool_name(stdin_text)
    file_path = _extract_tool_output_file(stdin_text)
    if tool_name and tool_name != "Write":
        return 0
    if not file_path or not _is_skeptic_signoff_path(file_path):
        return 0

    strict = _run(_py_cmd(str(validate_contract), "--strict"))
    _relay(strict)
    if strict.returncode != 0:
        return strict.returncode

    proc = _run(_py_cmd(str(skeptic_checker), file_path, "--mode", "format"))
    _relay(proc)
    return proc.returncode


def _resolve_artifact(root: Path, artifact: str) -> Tuple[int, str, str]:
    resolve_artifact, _ = _script_paths(root)
    proc = _run(
        _py_cmd(
            str(resolve_artifact),
            "--artifact",
            artifact,
            "--must-exist",
        ),
    )
    return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()


def _extract_assistant_message(stdin_text: str) -> str:
    if not stdin_text.strip():
        return ""
    payload = _parse_json_payload(stdin_text)
    if not payload:
        return stdin_text

    for key in ("assistant_message", "assistantMessage", "message", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    messages = payload.get("messages")
    if isinstance(messages, list):
        for msg in reversed(messages):
            if not isinstance(msg, dict):
                continue
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                return content
            if isinstance(content, list) and content:
                first = content[0]
                if isinstance(first, dict):
                    text = first.get("text")
                    if isinstance(text, str) and text.strip():
                        return text
    return ""


def _should_gate_stop(stdin_text: str) -> bool:
    msg = _extract_assistant_message(stdin_text)
    if not msg:
        return False
    lowered = msg.lower()
    return any(str(token).lower() in lowered for token in KEYWORDS)


def _emit_block(reason: str) -> None:
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": reason,
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            },
            ensure_ascii=False,
        )
    )


def _emit_pretool_deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            },
            ensure_ascii=False,
        )
    )


def _cmd_session_start(root: Path) -> int:
    _, validate_contract = _script_paths(root)
    strict = _run(_py_cmd(str(validate_contract), "--strict"))
    if strict.returncode != 0:
        _relay(strict)
        _emit_block("Session start blocked: tool contract validation failed.")
        return 0
    payload = run_preflight(root, case_root=_case_root_from_env())
    if payload["status"] != "passed":
        blockers = ", ".join(payload.get("blocking_codes") or ["unknown"])
        _emit_block(f"Session start blocked: {blockers}")
        return 0
    return 0


def _cmd_pretool_live(root: Path) -> int:
    _, validate_contract = _script_paths(root)
    strict = _run(_py_cmd(str(validate_contract), "--strict"))
    if strict.returncode != 0:
        _relay(strict)
        _emit_pretool_deny("Live tool blocked: tool contract validation failed.")
        return 0
    stdin_text = sys.stdin.read()
    tool_name = _extract_tool_name(stdin_text).strip().lower()
    if tool_name in {"view", "read", "glob", "grep", "show_file", "fetch_copilot_cli_documentation"}:
        return 0
    run_root = _run_root_from_env()
    if run_root is None:
        return 0
    payload = run_dispatch_readiness(root, run_root, platform=root.name)
    if payload["status"] != "passed":
        blockers = ", ".join(payload.get("blocking_codes") or ["unknown"])
        _emit_pretool_deny(f"Live tool blocked: {blockers}")
        return 0
    token_ref = str(os.environ.get("DEBUGGER_CAPABILITY_TOKEN", "")).strip()
    agent_id = str(os.environ.get("DEBUGGER_AGENT_ID", "")).strip()
    runtime_owner = str(os.environ.get("DEBUGGER_RUNTIME_OWNER", "")).strip()
    target_action = str(os.environ.get("DEBUGGER_TARGET_ACTION", "")).strip() or "live_investigation"
    target_path = _extract_tool_output_file(stdin_text)
    if token_ref and agent_id and runtime_owner:
        token = validate_capability_token(
            run_root,
            token_ref=token_ref,
            agent_id=agent_id,
            runtime_owner=runtime_owner,
            action=target_action,
            target_path=target_path,
        )
        if token["status"] != "passed":
            _emit_pretool_deny(f"Live tool blocked: {token['blocking_code']}")
            return 0
    return 0


def _cmd_posttool_artifact(root: Path) -> int:
    run_root = _run_root_from_env()
    if run_root is None:
        return 0
    file_path = _extract_tool_output_file(sys.stdin.read())
    token_ref = str(os.environ.get("DEBUGGER_CAPABILITY_TOKEN", "")).strip()
    agent_id = str(os.environ.get("DEBUGGER_AGENT_ID", "")).strip()
    runtime_owner = str(os.environ.get("DEBUGGER_RUNTIME_OWNER", "")).strip()
    target_action = str(os.environ.get("DEBUGGER_TARGET_ACTION", "")).strip() or "write_note"
    if token_ref and agent_id and runtime_owner and file_path:
        token = validate_capability_token(
            run_root,
            token_ref=token_ref,
            agent_id=agent_id,
            runtime_owner=runtime_owner,
            action=target_action,
            target_path=file_path,
        )
        if token["status"] != "passed":
            _emit_block(f"Artifact write blocked: {token['blocking_code']}")
            return 0
    return 0


def _cmd_stop_gate(root: Path, force: bool = False) -> int:
    stdin_text = sys.stdin.read()
    if (not force) and (not _should_gate_stop(stdin_text)):
        return 0

    _, causal_anchor_validator, counterfactual_validator, skeptic_checker = _validator_paths(root)
    _, validate_contract = _script_paths(root)
    run_audit = root / "common" / "hooks" / "utils" / "run_compliance_audit.py"

    errors: list[str] = []

    strict = _run(_py_cmd(str(validate_contract), "--strict"))
    if strict.returncode != 0:
        _relay(strict)
        errors.append("tool contract validation failed")

    rc_evi, evidence_path, evidence_err = _resolve_artifact(root, "session_evidence")
    rc_ske, signoff_path, signoff_err = _resolve_artifact(root, "skeptic_signoff")
    rc_act, action_chain_path, action_chain_err = _resolve_artifact(root, "action_chain")

    if rc_evi != 0:
        errors.append(f"missing session evidence artifact ({evidence_err or 'session_evidence.yaml'})")
    if rc_ske != 0:
        errors.append(f"missing skeptic signoff artifact ({signoff_err or 'skeptic_signoff.yaml'})")
    if rc_act != 0:
        errors.append(f"missing action chain artifact ({action_chain_err or 'action_chain.jsonl'})")

    if not errors:
        r0 = _run(_py_cmd(str(causal_anchor_validator), evidence_path))
        _relay(r0)
        if r0.returncode != 0:
            errors.append("causal anchor validator failed")

    if not errors:
        r1 = _run(_py_cmd(str(counterfactual_validator), evidence_path))
        _relay(r1)
        if r1.returncode != 0:
            errors.append("counterfactual validator failed")

        r2 = _run(_py_cmd(str(skeptic_checker), signoff_path, "--mode", "hypothesis"))
        _relay(r2)
        if r2.returncode != 0:
            errors.append("skeptic signoff checker failed")

    platform_key = root.name
    run_root = str(os.environ.get("DEBUGGER_RUN_ROOT", "")).strip()
    if not errors and run_audit.is_file():
        audit_cmd = _py_cmd(str(run_audit), "--platform", platform_key, "--strict")
        if run_root:
            audit_cmd.extend(["--run-root", run_root])
        audit_proc = _run(audit_cmd)
        _relay(audit_proc)
        if audit_proc.returncode != 0:
            errors.append("run compliance audit failed")

    if errors:
        _emit_block("Finalization blocked: " + "; ".join(errors))
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: codebuddy_hook_dispatch.py <session-start|pretool-live|posttool-artifact|write-bugcard|write-skeptic|stop-gate|stop-gate-force>",
            file=sys.stderr,
        )
        return 2

    mode = sys.argv[1].strip().lower()
    root = _debug_agent_root()

    if mode == "session-start":
        return _cmd_session_start(root)
    if mode == "pretool-live":
        return _cmd_pretool_live(root)
    if mode == "posttool-artifact":
        return _cmd_posttool_artifact(root)
    if mode == "write-bugcard":
        return _cmd_write_bugcard(root)
    if mode == "write-skeptic":
        return _cmd_write_skeptic(root)
    if mode == "stop-gate":
        return _cmd_stop_gate(root, force=False)
    if mode == "stop-gate-force":
        return _cmd_stop_gate(root, force=True)

    print(f"unknown mode: {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
