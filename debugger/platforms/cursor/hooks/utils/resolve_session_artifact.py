#!/usr/bin/env python3
"""Resolve session-scoped artifact paths for Cursor platform.

This script wraps the common resolve_session_artifact.py with
Cursor-specific defaults and environment handling.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def _debugger_root() -> Path:
    """Resolve debugger root from environment or script location."""
    env_root = os.environ.get("DEBUGGER_ROOT", "").strip()
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve session artifact path for Cursor platform")
    parser.add_argument(
        "--artifact",
        required=True,
        choices=["session_evidence", "skeptic_signoff", "action_chain"],
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

    root = args.root.resolve() if args.root else _debugger_root()
    common_resolver = root / "common" / "hooks" / "utils" / "resolve_session_artifact.py"

    if not common_resolver.is_file():
        print(f"[cursor-artifact] Error: Common resolver not found: {common_resolver}", file=sys.stderr)
        return 2

    cmd = [
        sys.executable,
        str(common_resolver),
        "--artifact",
        args.artifact,
    ]

    if args.session_id:
        cmd.extend(["--session-id", args.session_id])
    if args.must_exist:
        cmd.append("--must-exist")
    if args.root:
        cmd.extend(["--root", str(args.root)])

    result = subprocess.run(cmd, encoding="utf-8")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
