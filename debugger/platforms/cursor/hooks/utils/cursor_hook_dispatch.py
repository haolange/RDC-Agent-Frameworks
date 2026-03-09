#!/usr/bin/env python3
"""Cursor IDE hook dispatcher for RenderDoc/RDC GPU Debug Framework.

This script adapts the framework's quality hooks to work with Cursor IDE.
Since Cursor doesn't have native hook system like Claude Code, this dispatcher
provides a bridge to run validation checks.

Modes:
  - write-bugcard    : Validate BugCard on write to library
  - write-skeptic    : Validate Skeptic signoff on write
  - stop-gate        : Finalization gate check
  - stop-gate-force  : Force finalization gate check

Usage in Cursor:
  - Configure in .cursorrules or as pre-commit hooks
  - Or run manually: python cursor_hook_dispatch.py <mode>
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


def _debugger_root() -> Path:
    """Resolve debugger root from environment or script location."""
    env_root = os.environ.get("DEBUGGER_ROOT", "").strip()
    if env_root:
        return Path(env_root).resolve()
    # Fallback: navigate from platforms/cursor/hooks/utils/cursor_hook_dispatch.py
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


def _extract_write_path() -> str:
    """Extract file path from Cursor environment or arguments."""
    # Check environment variable set by Cursor or caller
    env_path = os.environ.get("CURSOR_WRITE_PATH", "").strip()
    if env_path:
        return env_path

    # Check for file path in command arguments
    for arg in sys.argv[2:]:
        if arg.endswith(".yaml") or arg.endswith(".yml"):
            return arg

    # Try to infer from git or file system
    return ""


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
    bugcard_validator, _, _, _ = _validator_paths(root)
    _, _, _, skeptic_checker = _validator_paths(root)
    _, validate_contract = _script_paths(root)
    file_path = _extract_write_path()
    if not file_path:
        print("[cursor-hook] No file path provided for BugCard validation", file=sys.stderr)
        return 0
    if not _is_bugcard_path(file_path):
        print(f"[cursor-hook] Skipping non-BugCard path: {file_path}")
        return 0

    print(f"[cursor-hook] Validating BugCard: {file_path}")

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
        print(f"[cursor-hook] Warning: missing session marker: {current}", file=sys.stderr)
        # Don't fail, just warn - Cursor may not have session tracking
        return 0

    session_id = current.read_text(encoding="utf-8").lstrip("\ufeff").strip()
    if (not session_id) or (session_id == "session-unset"):
        print(f"[cursor-hook] Warning: invalid current session id: {session_id!r}", file=sys.stderr)
        return 0

    try:
        safe_session_id = _validate_session_id(session_id)
    except ValueError as exc:
        print(f"[cursor-hook] Warning: invalid session id: {exc}", file=sys.stderr)
        return 0

    signoff_path = root / "common" / "knowledge" / "library" / "sessions" / safe_session_id / "skeptic_signoff.yaml"
    if not signoff_path.is_file():
        print(f"[cursor-hook] Warning: missing skeptic signoff artifact: {signoff_path}", file=sys.stderr)
        return 0

    proc2 = _run(_py_cmd(str(skeptic_checker), str(signoff_path), "--mode", "bugcard"))
    _relay(proc2)
    return proc2.returncode


def _cmd_write_skeptic(root: Path) -> int:
    _, _, _, skeptic_checker = _validator_paths(root)
    _, validate_contract = _script_paths(root)
    file_path = _extract_write_path()
    if not file_path:
        print("[cursor-hook] No file path provided for Skeptic validation", file=sys.stderr)
        return 0
    if not _is_skeptic_signoff_path(file_path):
        print(f"[cursor-hook] Skipping non-Skeptic path: {file_path}")
        return 0

    print(f"[cursor-hook] Validating Skeptic signoff: {file_path}")

    strict = _run(_py_cmd(str(validate_contract), "--strict"))
    _relay(strict)
    if strict.returncode != 0:
        return strict.returncode

    proc = _run(_py_cmd(str(skeptic_checker), file_path, "--mode", "format"))
    _relay(proc)
    return proc.returncode


def _resolve_artifact(root: Path, artifact: str) -> Tuple[int, str, str]:
    resolve_artifact_script, _ = _script_paths(root)
    proc = _run(
        _py_cmd(
            str(resolve_artifact_script),
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

    print("[cursor-hook] Running finalization gate checks...")

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

    platform_key = "cursor"
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
        return 1

    print("[cursor-hook] All finalization checks passed.")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: cursor_hook_dispatch.py <write-bugcard|write-skeptic|stop-gate|stop-gate-force> [file_path]",
            file=sys.stderr,
        )
        return 2

    mode = sys.argv[1].strip().lower()
    root = _debugger_root()

    if mode == "write-bugcard":
        return _cmd_write_bugcard(root)
    if mode == "write-skeptic":
        return _cmd_write_skeptic(root)
    if mode == "stop-gate":
        return _cmd_stop_gate(root, force=False)
    if mode == "stop-gate-force":
        return _cmd_stop_gate(root, force=True)

    print(f"[cursor-hook] Unknown mode: {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
