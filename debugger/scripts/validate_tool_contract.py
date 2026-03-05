#!/usr/bin/env python3
"""Validate debugger tool contract against rdx-mcp tool catalog.

Checks:
1) Unknown rd.* references in common/** and platforms/** (excluding design/**)
2) Action-chain tool calls:
   - unknown tool names
   - parameter key drift vs catalog param_names
   - missing session_id for tools that require it
3) Explicit call examples like rd.xxx.yyy(...) missing session_id for tools
   that require it
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Set


TEXT_EXTS = {".md", ".yaml", ".yml", ".json", ".jsonl", ".py"}
TOOL_RE = re.compile(r"rd\.[A-Za-z0-9_]+\.[A-Za-z0-9_\.]+")
CALL_RE = re.compile(r"(rd\.[A-Za-z0-9_]+\.[A-Za-z0-9_\.]+)\s*\(([^)]*)\)")


@dataclass
class Findings:
    unknown_tools: Dict[str, Set[str]] = field(default_factory=dict)
    action_unknown_tools: Dict[str, Set[str]] = field(default_factory=dict)
    action_param_drift: List[str] = field(default_factory=list)
    missing_session_examples: List[str] = field(default_factory=list)

    def has_issues(self) -> bool:
        return any(
            [
                self.unknown_tools,
                self.action_unknown_tools,
                self.action_param_drift,
                self.missing_session_examples,
            ],
        )


def _repo_root() -> Path:
    # .../extensions/debugger/scripts/validate_tool_contract.py
    return Path(__file__).resolve().parents[1]


def _default_catalog(debug_agent_root: Path) -> Path:
    return debug_agent_root.parent / "rdx-mcp" / "rdx" / "spec" / "tool_catalog_196.json"


def _load_catalog(catalog_path: Path) -> tuple[Set[str], Dict[str, Set[str]], Set[str]]:
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    tools = payload.get("tools", [])
    names: Set[str] = set()
    param_names: Dict[str, Set[str]] = {}
    requires_session: Set[str] = set()
    for item in tools:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        names.add(name)
        params = {str(p).strip() for p in item.get("param_names", []) if str(p).strip()}
        param_names[name] = params
        if "session_id" in params:
            requires_session.add(name)
    return names, param_names, requires_session


def _iter_scan_files(debug_agent_root: Path) -> Iterable[Path]:
    for rel in ("common", "platforms"):
        base = debug_agent_root / rel
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in TEXT_EXTS:
                continue
            # Keep design excluded even if it appears under scanned roots in future.
            if "design" in path.parts:
                continue
            yield path


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _check_unknown_tools(
    files: Iterable[Path],
    known_tools: Set[str],
) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for path in files:
        refs = set(TOOL_RE.findall(_read_text(path)))
        unknown = {ref for ref in refs if ref not in known_tools}
        if unknown:
            out[str(path)] = unknown
    return out


def _check_action_chains(
    debug_agent_root: Path,
    known_tools: Set[str],
    tool_params: Dict[str, Set[str]],
    requires_session: Set[str],
) -> tuple[Dict[str, Set[str]], List[str]]:
    action_unknown: Dict[str, Set[str]] = {}
    drift: List[str] = []
    traces_dir = debug_agent_root / "common" / "knowledge" / "traces" / "action_chains"
    if not traces_dir.is_dir():
        return action_unknown, drift

    for jsonl in sorted(traces_dir.glob("*.jsonl")):
        unknown_here: Set[str] = set()
        for idx, line in enumerate(_read_text(jsonl).splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                drift.append(f"{jsonl}:{idx}: invalid jsonl line: {exc}")
                continue
            steps = payload.get("steps", [])
            if not isinstance(steps, list):
                drift.append(f"{jsonl}:{idx}: steps must be a list")
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if step.get("action_type") != "tool_call":
                    continue
                tool = str(step.get("tool", "")).strip()
                params = step.get("params", {})
                if tool not in known_tools:
                    if tool:
                        unknown_here.add(tool)
                    continue
                if not isinstance(params, dict):
                    drift.append(f"{jsonl}:{idx}: tool {tool} params must be object")
                    continue
                allowed = tool_params.get(tool, set())
                extra = sorted(k for k in params.keys() if k not in allowed)
                if extra:
                    drift.append(
                        f"{jsonl}:{idx}: tool {tool} has unexpected params {extra}; allowed={sorted(allowed)}",
                    )
                if tool in requires_session and "session_id" not in params:
                    drift.append(f"{jsonl}:{idx}: tool {tool} missing required session_id")
        if unknown_here:
            action_unknown[str(jsonl)] = unknown_here
    return action_unknown, drift


def _check_session_examples(
    files: Iterable[Path],
    requires_session: Set[str],
) -> List[str]:
    missing: List[str] = []
    for path in files:
        text = _read_text(path)
        for lineno, line in enumerate(text.splitlines(), start=1):
            for tool, arg_text in CALL_RE.findall(line):
                if tool in requires_session and "session_id" not in arg_text:
                    missing.append(f"{path}:{lineno}: {tool}(...) missing session_id in example")
    return missing


def _print_findings(findings: Findings) -> None:
    if findings.unknown_tools:
        print("[unknown rd.* references]")
        for file_path in sorted(findings.unknown_tools):
            refs = ", ".join(sorted(findings.unknown_tools[file_path]))
            print(f"  - {file_path}: {refs}")
    if findings.action_unknown_tools:
        print("[action_chains unknown tools]")
        for file_path in sorted(findings.action_unknown_tools):
            refs = ", ".join(sorted(findings.action_unknown_tools[file_path]))
            print(f"  - {file_path}: {refs}")
    if findings.action_param_drift:
        print("[action_chains param drift]")
        for row in findings.action_param_drift:
            print(f"  - {row}")
    if findings.missing_session_examples:
        print("[example calls missing session_id]")
        for row in findings.missing_session_examples:
            print(f"  - {row}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate debugger tool contract")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=None,
        help="Path to tool_catalog_196.json (default: ../rdx-mcp/rdx/spec/tool_catalog_196.json)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when findings exist",
    )
    args = parser.parse_args()

    debug_agent_root = _repo_root()
    catalog = args.catalog or _default_catalog(debug_agent_root)
    if not catalog.is_file():
        print(f"catalog not found: {catalog}")
        return 2

    known_tools, tool_params, requires_session = _load_catalog(catalog)

    files = list(_iter_scan_files(debug_agent_root))
    findings = Findings()
    findings.unknown_tools = _check_unknown_tools(files, known_tools)
    findings.action_unknown_tools, findings.action_param_drift = _check_action_chains(
        debug_agent_root,
        known_tools,
        tool_params,
        requires_session,
    )
    findings.missing_session_examples = _check_session_examples(files, requires_session)

    if findings.has_issues():
        _print_findings(findings)
        return 1 if args.strict else 0

    print("tool contract validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
