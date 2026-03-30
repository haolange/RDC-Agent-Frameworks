#!/usr/bin/env python3
"""Validate debugger tool references against the configured platform catalog."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

TEXT_EXTS = {".md", ".yaml", ".yml", ".json", ".jsonl", ".py"}
TOOL_PATTERN = r"(?<![A-Za-z0-9_\.])(?P<tool>rd\.[A-Za-z0-9_]+\.[A-Za-z0-9_\.]+)"
TOOL_RE = re.compile(TOOL_PATTERN)
CALL_RE = re.compile(TOOL_PATTERN + r"\s*\(([^)]*)\)")
ENV_CATALOG = "DEBUGGER_PLATFORM_CATALOG"
EXPECTED_TOOLS_ROOT = "tools"
EXPECTED_RUNTIME_MODE = "worker_staged"
SNAPSHOT_PATH = Path("common") / "config" / "tool_catalog.snapshot.json"
BANNED_SNIPPETS = {
    "error_message": "use canonical error.message instead of legacy error_message",
    "--connect": "legacy CLI connect flag removed; CLI is always daemon-backed",
    "直接本地 runtime": "framework docs must not describe direct runtime ownership",
    "__CONFIGURE_TOOLS_ROOT__": "legacy configurable tools_root flow removed; use the package-local tools/ source payload",
    "配置 `paths.tools_root`": "legacy manual tools_root configuration removed; use the package-local tools/ source payload",
    "configure `paths.tools_root`": "legacy manual tools_root configuration removed; use the package-local tools/ source payload",
}


@dataclass
class Findings:
    unknown_tools: dict[str, set[str]] = field(default_factory=dict)
    missing_prerequisite_examples: list[str] = field(default_factory=list)
    banned_snippets: list[str] = field(default_factory=list)

    def has_issues(self) -> bool:
        return any([self.unknown_tools, self.missing_prerequisite_examples, self.banned_snippets])


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_source_root(cur: Path) -> bool:
    return (cur / "platforms").is_dir()


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc.msg} (line {exc.lineno}, column {exc.colno}).") from exc


def adapter_payload(cur: Path) -> dict:
    return read_json(cur / "common" / "config" / "platform_adapter.json")


def resolve_tools_root(cur: Path) -> Path:
    payload = adapter_payload(cur)
    raw_root = str(payload.get("paths", {}).get("tools_source_root", "")).strip()
    if raw_root != EXPECTED_TOOLS_ROOT:
        raise ValueError(
            f"platform_adapter.json must keep paths.tools_source_root='{EXPECTED_TOOLS_ROOT}' and treat tools/ as a package-local source payload"
        )
    runtime_mode = str(payload.get("runtime", {}).get("mode", "")).strip()
    if runtime_mode != EXPECTED_RUNTIME_MODE:
        raise ValueError(
            f"platform_adapter.json must keep runtime.mode='{EXPECTED_RUNTIME_MODE}' for daemon-owned worker staging"
        )
    tools_root = (cur / EXPECTED_TOOLS_ROOT).resolve()
    required_paths = [
        str(item).strip()
        for item in payload.get("validation", {}).get("required_paths", [])
        if str(item).strip()
    ]
    if not required_paths:
        raise ValueError("platform_adapter.json missing validation.required_paths")
    missing = [rel for rel in required_paths if not (tools_root / rel).is_file()]
    if missing:
        missing_paths = ", ".join(str(tools_root / rel) for rel in missing)
        raise ValueError(f"package-local tools source payload validation failed: missing {missing_paths}")
    return tools_root


def default_catalog(cur: Path) -> Path:
    env_override = os.environ.get(ENV_CATALOG, "").strip()
    if env_override:
        return Path(env_override).resolve()
    return (resolve_tools_root(cur) / "spec" / "tool_catalog.json").resolve()


def source_snapshot(cur: Path) -> Path:
    return (cur / SNAPSHOT_PATH).resolve()


def load_catalog(path: Path) -> tuple[set[str], dict[str, list[dict[str, str]]]]:
    payload = read_json(path)
    names = {
        str(item.get("name", "")).strip()
        for item in payload.get("tools", [])
        if str(item.get("name", "")).strip()
    }
    requires_prereq = {
        str(item.get("name", "")).strip(): [
            {
                "requires": str(pr.get("requires", "")).strip(),
                "when": str(pr.get("when", "")).strip(),
            }
            for pr in item.get("prerequisites", [])
            if isinstance(pr, dict) and str(pr.get("requires", "")).strip()
        ]
        for item in payload.get("tools", [])
        if str(item.get("name", "")).strip()
    }
    return names, requires_prereq


def iter_scan_files(cur: Path) -> list[Path]:
    roots = (
        [cur / "common", cur / "platforms"]
        if is_source_root(cur)
        else [cur]
        + [
            cur / name
            for name in ("common", "docs", "scripts", "agents", "skills", "hooks", "references", "workflows", ".claude", ".github")
            if (cur / name).exists()
        ]
    )
    return [
        path
        for base in roots
        for path in ([base] if base.is_file() else base.rglob("*"))
        if path.is_file() and path.suffix.lower() in TEXT_EXTS and "design" not in path.parts
    ]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="ignore")


def _tool_refs(text: str) -> set[str]:
    return {match.group("tool") for match in TOOL_RE.finditer(text)}


def _is_known_field_path_reference(ref: str, known_tools: set[str]) -> bool:
    parts = str(ref or "").split(".")
    if len(parts) <= 3:
        return False
    return ".".join(parts[:3]) in known_tools


def check_unknown_tools(files: list[Path], known_tools: set[str]) -> dict[str, set[str]]:
    findings: dict[str, set[str]] = {}
    for path in files:
        refs = {
            ref
            for ref in _tool_refs(read_text(path))
            if ref not in known_tools and not _is_known_field_path_reference(ref, known_tools)
        }
        if refs:
            findings[str(path)] = refs
    return findings


def check_prerequisite_examples(files: list[Path], prerequisites: dict[str, list[dict[str, str]]]) -> list[str]:
    rows: list[str] = []
    for path in files:
        for lineno, line in enumerate(read_text(path).splitlines(), start=1):
            for match in CALL_RE.finditer(line):
                tool = match.group("tool")
                arg_text = match.group(2)
                for prereq in prerequisites.get(tool, []):
                    required = prereq.get("requires", "")
                    when = prereq.get("when", "")
                    if when == "options.remote_id_present" and "remote_id" not in arg_text:
                        continue
                    if required == "session_id" and "session_id" not in arg_text:
                        rows.append(f"{path}:{lineno}: {tool}(...) missing session_id prerequisite in example")
                    if required == "capture_file_id" and "capture_file_id" not in arg_text:
                        rows.append(f"{path}:{lineno}: {tool}(...) missing capture_file_id prerequisite in example")
                    if required == "remote_id" and "remote_id" not in arg_text and "options.remote_id" not in arg_text:
                        rows.append(f"{path}:{lineno}: {tool}(...) missing remote_id prerequisite in example")
    return rows


def check_banned_snippets(files: list[Path]) -> list[str]:
    rows: list[str] = []
    for path in files:
        if path.name == "tool_catalog.snapshot.json" or path.suffix.lower() == ".py":
            continue
        text = read_text(path)
        for snippet, reason in BANNED_SNIPPETS.items():
            if snippet in text:
                rows.append(f"{path}: banned snippet `{snippet}` ({reason})")
    return rows


def print_findings(findings: Findings) -> None:
    if findings.unknown_tools:
        print("[unknown rd.* references]")
        for file_path in sorted(findings.unknown_tools):
            print(" - " + file_path + ": " + ", ".join(sorted(findings.unknown_tools[file_path])))
    if findings.missing_prerequisite_examples:
        print("[example calls missing prerequisites]")
        for row in findings.missing_prerequisite_examples:
            print(" - " + row)
    if findings.banned_snippets:
        print("[banned legacy snippets]")
        for row in findings.banned_snippets:
            print(" - " + row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate debugger tool contract")
    parser.add_argument("--catalog", type=Path, default=None, help=f"Path to platform tool catalog (default: adapter config or {ENV_CATALOG})")
    parser.add_argument("--mode", choices=("source", "package"), default=None, help="Validate against the source snapshot or a configured platform package")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when findings exist")
    args = parser.parse_args()

    cur = root()
    mode = args.mode or ("source" if is_source_root(cur) else "package")
    try:
        if args.catalog:
            catalog = args.catalog.resolve()
        elif mode == "source":
            catalog = source_snapshot(cur)
        else:
            catalog = default_catalog(cur)
    except ValueError as exc:
        print(str(exc))
        return 2
    if not catalog.is_file():
        print(f"catalog not found: {catalog}")
        return 2
    try:
        known_tools, prerequisites = load_catalog(catalog)
    except ValueError as exc:
        print(str(exc))
        return 2
    files = iter_scan_files(cur)
    findings = Findings(
        check_unknown_tools(files, known_tools),
        check_prerequisite_examples(files, prerequisites),
        check_banned_snippets(files),
    )
    if findings.has_issues():
        print_findings(findings)
        return 1 if args.strict else 0
    print(f"tool contract validation passed ({catalog})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
