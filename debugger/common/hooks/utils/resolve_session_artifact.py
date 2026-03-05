#!/usr/bin/env python3
"""Resolve session-scoped artifact paths for debugger hooks."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ARTIFACT_FILES = {
    "session_evidence": "session_evidence.yaml",
    "skeptic_signoff": "skeptic_signoff.yaml",
    "action_chain": "action_chain.jsonl",
}

_SAFE_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _debug_agent_root() -> Path:
    # .../extensions/debugger/common/hooks/utils/resolve_session_artifact.py
    return Path(__file__).resolve().parents[3]


def _validate_session_id(session_id: str) -> str:
    sid = str(session_id or "").strip()
    if not sid:
        raise ValueError("empty session id")
    if sid in {".", ".."}:
        raise ValueError(f"invalid session id: {sid!r}")
    if not _SAFE_SESSION_ID_RE.match(sid):
        raise ValueError(
            "invalid session id (must be a single path-safe token): "
            f"{sid!r}",
        )
    return sid


def _resolve_session_id(root: Path, session_id_arg: str | None) -> str:
    if session_id_arg:
        return _validate_session_id(session_id_arg)
    current = root / "common" / "knowledge" / "library" / "sessions" / ".current_session"
    if not current.is_file():
        raise FileNotFoundError(
            f"missing current session marker: {current} (pass --session-id or create this file)",
        )
    value = current.read_text(encoding="utf-8").lstrip("\ufeff").strip()
    if not value:
        raise ValueError(f"empty current session marker: {current}")
    return _validate_session_id(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve session artifact path")
    parser.add_argument(
        "--artifact",
        required=True,
        choices=sorted(ARTIFACT_FILES.keys()),
        help="artifact key",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="session id; defaults to common/knowledge/library/sessions/.current_session",
    )
    parser.add_argument(
        "--must-exist",
        action="store_true",
        help="fail when resolved artifact does not exist",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="debugger root override",
    )
    args = parser.parse_args()

    root = args.root.resolve() if args.root else _debug_agent_root()
    try:
        session_id = _resolve_session_id(root, args.session_id)
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 2

    artifact_name = ARTIFACT_FILES[args.artifact]
    resolved = root / "common" / "knowledge" / "library" / "sessions" / session_id / artifact_name
    if args.must_exist and not resolved.is_file():
        print(f"artifact not found: {resolved}", file=sys.stderr)
        return 3

    print(str(resolved))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
