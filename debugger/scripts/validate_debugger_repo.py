#!/usr/bin/env python3
"""Repository-level debugger validator."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def _print_proc(proc: subprocess.CompletedProcess[str]) -> None:
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)


def _surface_supported(platform_caps: dict, surface: str) -> bool:
    if surface == "workflow":
        return bool(platform_caps.get("coordination_mode") == "workflow_stage" or platform_caps.get("degradation_mode") == "workflow-package")
    if surface == "agents":
        surface = "custom_agents"
    caps = platform_caps.get("capabilities") or {}
    slot = caps.get(surface) or {}
    return bool(slot.get("supported"))


def _compliance_findings(root: Path) -> list[str]:
    findings: list[str] = []
    compliance = _read_json(root / "common" / "config" / "framework_compliance.json")
    caps = _read_json(root / "common" / "config" / "platform_capabilities.json")
    platforms = compliance.get("platforms") or {}
    cap_platforms = caps.get("platforms") or {}

    if set(platforms) != set(cap_platforms):
        findings.append("framework_compliance.json and platform_capabilities.json platform keys differ")

    for key, rules in sorted(platforms.items()):
        platform_caps = cap_platforms.get(key)
        if not isinstance(platform_caps, dict):
            findings.append(f"missing platform_capabilities entry for {key}")
            continue

        expected_mode = str(rules.get("coordination_mode", "")).strip()
        actual_mode = str(platform_caps.get("coordination_mode", "")).strip()
        if expected_mode != actual_mode:
            findings.append(f"{key}: coordination_mode mismatch ({expected_mode} != {actual_mode})")

        for surface in rules.get("required_surfaces") or []:
            if not _surface_supported(platform_caps, str(surface)):
                findings.append(f"{key}: required surface '{surface}' is not supported by platform_capabilities")

        for rel in platform_caps.get("required_paths") or []:
            path = root / rel
            if not path.exists():
                findings.append(f"{key}: required path missing: {path}")

        if rules.get("workflow_required") and actual_mode != "workflow_stage":
            findings.append(f"{key}: workflow_required=true but coordination_mode is not workflow_stage")

    live_sessions = root / "common" / "knowledge" / "library" / "sessions"
    allowed = set(compliance["runtime_artifact_contract"]["allowed_live_library_session_entries"])
    if live_sessions.is_dir():
        for child in live_sessions.iterdir():
            if child.name in allowed:
                continue
            if child.is_dir() and not any(child.iterdir()):
                continue
            if child.name not in allowed:
                findings.append(f"live library sessions contains example or unexpected entry: {child}")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate debugger repo")
    parser.add_argument("--strict", action="store_true", help="return non-zero when findings exist")
    args = parser.parse_args()

    root = _root()
    commands = [
        [sys.executable, str(root / "scripts" / "sync_platform_scaffolds.py"), "--check"],
        [sys.executable, str(root / "scripts" / "validate_platform_layout.py"), "--strict"],
        [sys.executable, str(root / "scripts" / "validate_tool_contract.py"), "--mode", "source", "--strict"],
    ]

    findings: list[str] = []
    for command in commands:
        proc = _run(command, root.parent)
        _print_proc(proc)
        if proc.returncode != 0:
            findings.append(f"command failed: {' '.join(command)}")

    findings.extend(_compliance_findings(root))

    if findings:
        print("[debugger repo findings]")
        for row in findings:
            print(f" - {row}")
        return 1 if args.strict else 0

    print("debugger repo validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
