#!/usr/bin/env python3
"""Causal anchor validator wrapper for Cursor platform.

This script delegates to the common causal_anchor_validator.py with
Cursor-specific output formatting and environment handling.

Usage:
  python causal_anchor_validator.py <session_evidence.yaml>

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
    parser = argparse.ArgumentParser(description="Causal anchor validator for Cursor platform")
    parser.add_argument("file_path", help="path to session_evidence.yaml")
    parser.add_argument("--root", type=Path, default=None, help="debugger root override")
    args = parser.parse_args()

    root = args.root.resolve() if args.root else _debugger_root()
    common_validator = root / "common" / "hooks" / "validators" / "causal_anchor_validator.py"

    if not common_validator.is_file():
        print(f"[cursor-causal] Error: Common validator not found: {common_validator}", file=sys.stderr)
        return 2

    cmd = [sys.executable, str(common_validator), args.file_path]

    result = subprocess.run(cmd, encoding="utf-8")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
