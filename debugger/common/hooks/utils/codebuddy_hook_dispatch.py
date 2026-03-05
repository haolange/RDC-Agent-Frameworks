#!/usr/bin/env python3
"""Safe hook dispatcher for Code Buddy and Claude-style hooks.

Modes:
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
from typing import Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

KEYWORDS = (
    "DEBUGGER_FINAL_VERDICT",
    "最终裁决",
    "根因确认",
    "结案",
    "final verdict",
    "case closed",
)

_SAFE_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _normalize_path_text(value: str) -> str:
    return str(value or "").strip().replace("\\", "/")


def _is_yaml_path(path: str) -> bool:
    lowered = _normalize_path_text(path).lower()
    return lowered.endswith(".yaml") or lowered.endswith(".yml")


def _is_bugcard_path(path: str) -> bool:
    lowered = _normalize_path_text(path).lower()
    return ("/knowledge/library/bugcards/" in lowered) and _is_yaml_path(lowered)


def _is_skeptic_signoff_path(path: str) -> bool:
    lowered = _normalize_path_text(path).lower()
    if not _is_yaml_path(lowered):
        return False
    return ("/knowledge/library/sessions/" in lowered) and (
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


def _validator_paths(root: Path) -> tuple[Path, Path, Path]:
    validators = root / "common" / "hooks" / "validators"
    return (
        validators / "bugcard_validator.py",
        validators / "counterfactual_validator.py",
        validators / "skeptic_signoff_checker.py",
    )


def _script_paths(root: Path) -> tuple[Path, Path]:
    resolve_artifact = root / "common" / "hooks" / "utils" / "resolve_session_artifact.py"
    validate_contract = root / "scripts" / "validate_tool_contract.py"
    return resolve_artifact, validate_contract


def _extract_tool_output_file() -> str:
    payload = os.environ.get("CODEBUDDY_TOOL_INPUT", "").strip()
    if payload:
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            obj = {}
        if isinstance(obj, dict):
            for key in ("file_path", "path", "output_file", "output_path", "file"):
                file_path = str(obj.get(key, "")).strip()
                if file_path:
                    return file_path
            nested = obj.get("result")
            if isinstance(nested, dict):
                for key in ("file_path", "path", "output_file", "output_path", "file"):
                    file_path = str(nested.get(key, "")).strip()
                    if file_path:
                        return file_path
    return str(os.environ.get("TOOL_OUTPUT_FILE", "")).strip()


def _relay(proc: subprocess.CompletedProcess[str]) -> None:
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)


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
    bugcard_validator, _, _ = _validator_paths(root)
    _, _, skeptic_checker = _validator_paths(root)
    _, validate_contract = _script_paths(root)
    file_path = _extract_tool_output_file()
    if not file_path:
        return 0
    if not _is_bugcard_path(file_path):
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
    _, _, skeptic_checker = _validator_paths(root)
    _, validate_contract = _script_paths(root)
    file_path = _extract_tool_output_file()
    if not file_path:
        return 0
    if not _is_skeptic_signoff_path(file_path):
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
    try:
        payload = json.loads(stdin_text)
    except json.JSONDecodeError:
        return stdin_text

    if isinstance(payload, dict):
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
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


def _cmd_stop_gate(root: Path, force: bool = False) -> int:
    stdin_text = sys.stdin.read()
    if (not force) and (not _should_gate_stop(stdin_text)):
        return 0

    _, counterfactual_validator, skeptic_checker = _validator_paths(root)
    _, validate_contract = _script_paths(root)

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
        r1 = _run(_py_cmd(str(counterfactual_validator), evidence_path))
        _relay(r1)
        if r1.returncode != 0:
            errors.append("counterfactual validator failed")

        r2 = _run(_py_cmd(str(skeptic_checker), signoff_path, "--mode", "hypothesis"))
        _relay(r2)
        if r2.returncode != 0:
            errors.append("skeptic signoff checker failed")

    if errors:
        _emit_block("Finalization blocked: " + "; ".join(errors))
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: codebuddy_hook_dispatch.py <write-bugcard|write-skeptic|stop-gate|stop-gate-force>",
            file=sys.stderr,
        )
        return 2

    mode = sys.argv[1].strip().lower()
    root = _debug_agent_root()

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
