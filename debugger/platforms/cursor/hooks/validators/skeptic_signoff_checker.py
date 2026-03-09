#!/usr/bin/env python3
"""Skeptic signoff checker wrapper for Cursor platform.

This script delegates to the common skeptic_signoff_checker.py with
Cursor-specific output formatting and environment handling.

Usage:
  python skeptic_signoff_checker.py <skeptic_signoff.yaml> [--mode {format|bugcard|hypothesis}]

Returns:
  0 - validation passed
  1 - validation failed
  2 - file/dependency error
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
    parser = argparse.ArgumentParser(description="Skeptic signoff checker for Cursor platform")
    parser.add_argument("file_path", help="path to skeptic_signoff.yaml")
    parser.add_argument(
        "--mode",
        choices=["format", "bugcard", "hypothesis"],
        default="format",
        help="validation mode",
    )
    parser.add_argument("--root", type=Path, default=None, help="debugger root override")
    args = parser.parse_args()

    root = args.root.resolve() if args.root else _debugger_root()
    common_checker = root / "common" / "hooks" / "validators" / "skeptic_signoff_checker.py"

    if not common_checker.is_file():
        print(f"[cursor-skeptic] Error: Common checker not found: {common_checker}", file=sys.stderr)
        return 2

    cmd = [sys.executable, str(common_checker), args.file_path, "--mode", args.mode]

    result = subprocess.run(cmd, encoding="utf-8")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
