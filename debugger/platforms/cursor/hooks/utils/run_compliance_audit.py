#!/usr/bin/env python3
"""Run compliance audit for Cursor platform.

This script wraps the common run_compliance_audit.py with Cursor-specific
defaults and environment handling.
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
    parser = argparse.ArgumentParser(description="Run compliance audit for Cursor platform")
    parser.add_argument("--run-root", type=Path, default=None, help="workspace run root")
    parser.add_argument("--strict", action="store_true", help="return non-zero on failure")
    parser.add_argument("--root", type=Path, default=None, help="debugger root override")
    args = parser.parse_args()

    root = args.root.resolve() if args.root else _debugger_root()
    common_audit = root / "common" / "hooks" / "utils" / "run_compliance_audit.py"

    if not common_audit.is_file():
        print(f"[cursor-audit] Error: Common audit script not found: {common_audit}", file=sys.stderr)
        return 2

    cmd = [sys.executable, str(common_audit), "--platform", "cursor"]

    if args.run_root:
        cmd.extend(["--run-root", str(args.run_root)])
    if args.strict:
        cmd.append("--strict")
    if args.root:
        cmd.extend(["--root", str(args.root)])

    result = subprocess.run(cmd, encoding="utf-8")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
