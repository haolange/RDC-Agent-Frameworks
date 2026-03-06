#!/usr/bin/env python3
"""Validate platform layout against platform_capabilities.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _debugger_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate platform layouts")
    parser.add_argument("--strict", action="store_true", help="Return non-zero on any missing path")
    args = parser.parse_args()

    debugger_root = _debugger_root()
    config_path = debugger_root / "common" / "config" / "platform_capabilities.json"
    payload = _load_json(config_path)

    missing: list[str] = []
    for platform_key, meta in payload.get("platforms", {}).items():
        for rel_path in meta.get("required_paths", []):
            candidate = debugger_root / rel_path
            if not candidate.exists():
                missing.append(f"{platform_key}: missing {candidate}")

    if missing:
        print("[platform layout findings]")
        for row in missing:
            print(f"  - {row}")
        return 1 if args.strict else 0

    print(f"platform layout validation passed ({config_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
