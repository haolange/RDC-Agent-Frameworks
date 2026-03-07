#!/usr/bin/env python3
"""Causal anchor gate validator for RenderDoc/RDC GPU Debug."""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import yaml
except ModuleNotFoundError:
    req = Path(__file__).resolve().parents[1] / "requirements.txt"
    print("Missing dependency 'PyYAML'; cannot parse YAML.")
    print(f"Install dependencies with: python3 -m pip install -r {req}")
    sys.exit(2)

ANSI_RED = "\033[91m"
ANSI_GREEN = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_RESET = "\033[0m"
ALLOWED_TYPES = {"first_bad_event", "first_divergence_event", "root_drawcall", "root_expression"}


def _nonempty_str(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_causal_anchor(data: dict) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if not isinstance(data, dict):
        return False, ["session evidence must be a YAML/JSON object"]

    anchor = data.get("causal_anchor")
    evidence = data.get("evidence", data.get("evidence_chain", []))
    if not isinstance(evidence, list):
        return False, ["evidence / evidence_chain must be a list"]
    if not isinstance(anchor, dict):
        return False, ["missing causal_anchor object"]

    if anchor.get("type") not in ALLOWED_TYPES:
        issues.append(f"invalid causal_anchor.type: {anchor.get('type')!r}; allowed: {sorted(ALLOWED_TYPES)}")
    if not _nonempty_str(anchor.get("ref")):
        issues.append("causal_anchor.ref must not be empty")
    if not _nonempty_str(anchor.get("established_by")):
        issues.append("causal_anchor.established_by must not be empty")
    if not _nonempty_str(anchor.get("justification")):
        issues.append("causal_anchor.justification must not be empty")

    direct_anchor = [
        item for item in evidence
        if isinstance(item, dict)
        and item.get("type") == "causal_anchor_evidence"
        and _nonempty_str(item.get("anchor_ref") or item.get("ref"))
    ]
    has_visual_only = any(isinstance(item, dict) and item.get("type") == "visual_fallback_observation" for item in evidence)
    has_direct_tool = any(isinstance(item, dict) and item.get("type") in {"tool_execution", "causal_anchor_evidence"} for item in evidence)

    if not direct_anchor:
        issues.append("missing direct causal_anchor_evidence record")
    if has_visual_only and not direct_anchor:
        issues.append("visual_fallback_observation exists without causal_anchor_evidence support")
    if evidence and not has_direct_tool:
        issues.append("evidence contains no direct tool evidence")

    return (not issues), issues


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 causal_anchor_validator.py <session_evidence.yaml>")
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"{ANSI_RED}Error: file not found - {path}{ANSI_RESET}")
        return 2

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"{ANSI_RED}Error: YAML parse failed - {exc}{ANSI_RESET}")
        return 2

    ok, issues = validate_causal_anchor(data)
    if ok:
        anchor = data.get("causal_anchor", {})
        print(f"{ANSI_GREEN}OK causal anchor - {anchor.get('type')} / {anchor.get('ref')}{ANSI_RESET}")
        return 0

    print(f"{ANSI_RED}FAIL causal anchor gate{ANSI_RESET}\n")
    for issue in issues:
        print(f"  - {issue}")
    print(f"\n{ANSI_YELLOW}Add a causal anchor or re-anchor the investigation before finalization.{ANSI_RESET}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
