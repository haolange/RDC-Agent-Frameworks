#!/usr/bin/env python3
"""Validate fixed debugger-to-tools binding for source and copied platform layouts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ESSENTIAL_COMMON_DOCS = [
    "README.md",
    "common/README.md",
    "common/AGENT_CORE.md",
    "common/docs/cli-mode-reference.md",
    "common/docs/model-routing.md",
    "common/docs/platform-capability-matrix.md",
    "common/docs/platform-capability-model.md",
    "common/docs/runtime-coordination-model.md",
    "common/docs/workspace-layout.md",
]
VFS_TOOLS = {
    "rd.vfs.ls",
    "rd.vfs.cat",
    "rd.vfs.tree",
    "rd.vfs.resolve",
}
SESSION_TOOLS = {
    "rd.session.get_context",
    "rd.session.update_context",
    "rd.session.list_sessions",
    "rd.session.select_session",
    "rd.session.resume",
}
CORE_DISCOVERY_TOOLS = {
    "rd.core.get_operation_history",
    "rd.core.get_runtime_metrics",
    "rd.core.list_tools",
    "rd.core.search_tools",
    "rd.core.get_tool_graph",
}
REQUIRED_FRAMEWORK_TOOLS = VFS_TOOLS | SESSION_TOOLS | CORE_DISCOVERY_TOOLS
COMMON_PLACEHOLDER_MARKERS = (
    "Platform Local Common Placeholder",
    "当前目录是平台本地 `common/` 的最小占位目录",
)
EXPECTED_TOOLS_SOURCE_ROOT = "tools"
EXPECTED_RUNTIME_MODE = "worker_staged"


def _default_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc.msg} (line {exc.lineno}, column {exc.colno}).") from exc


def _is_source_root(root: Path) -> bool:
    return (root / "platforms").is_dir()


def _platform_adapter_path(root: Path) -> Path:
    return root / "common" / "config" / "platform_adapter.json"


def _snapshot_path(root: Path) -> Path:
    return root / "common" / "config" / "tool_catalog.snapshot.json"


def _common_readme_path(root: Path) -> Path:
    return root / "common" / "README.md"


def _resolve_tools_root(root: Path, payload: dict[str, Any]) -> Path:
    raw = str(payload.get("paths", {}).get("tools_source_root", "")).strip()
    if raw != EXPECTED_TOOLS_SOURCE_ROOT:
        raise ValueError(
            f"platform_adapter.json must keep paths.tools_source_root='{EXPECTED_TOOLS_SOURCE_ROOT}' and treat tools/ as a package-local source payload"
        )
    runtime_mode = str(payload.get("runtime", {}).get("mode", "")).strip()
    if runtime_mode != EXPECTED_RUNTIME_MODE:
        raise ValueError(
            f"platform_adapter.json must keep runtime.mode='{EXPECTED_RUNTIME_MODE}' for daemon-owned worker staging"
        )
    return (root / EXPECTED_TOOLS_SOURCE_ROOT).resolve()


def _is_tools_placeholder(tools_root: Path) -> bool:
    if not tools_root.is_dir():
        return False
    children = list(tools_root.iterdir())
    return len(children) == 1 and children[0].name == "README.md"


def _is_common_placeholder(common_readme: Path) -> bool:
    if not common_readme.is_file():
        return False
    text = common_readme.read_text(encoding="utf-8-sig", errors="ignore")
    return any(marker in text for marker in COMMON_PLACEHOLDER_MARKERS)


def validate_binding(root: Path, *, platform: str = "") -> list[str]:
    findings: list[str] = []
    adapter_path = _platform_adapter_path(root)
    if not adapter_path.is_file():
        return [f"missing adapter config: {adapter_path}"]

    try:
        payload = _read_json(adapter_path)
        tools_root = _resolve_tools_root(root, payload)
    except ValueError as exc:
        findings.append(str(exc))
        return findings

    common_readme = _common_readme_path(root)
    if not common_readme.is_file():
        findings.append(f"missing shared debugger doc: {common_readme}")
    elif _is_common_placeholder(common_readme):
        findings.append(
            "common/README.md is still a platform placeholder - copy debugger/common/ into the platform root common/ again"
        )

    if _is_tools_placeholder(tools_root):
        findings.append(
            "tools/ is a placeholder source payload directory - copy RDC-Agent-Tools into the platform root tools/ then re-run"
        )
        return findings

    required_paths = [
        str(item).strip()
        for item in payload.get("validation", {}).get("required_paths", [])
        if str(item).strip()
    ]
    if not required_paths:
        findings.append("platform_adapter.json missing validation.required_paths")
    for rel in required_paths:
        if not (tools_root / rel).is_file():
            findings.append(f"package-local tools source payload validation failed: missing {tools_root / rel}")

    for rel in ESSENTIAL_COMMON_DOCS:
        if not (root / rel).is_file():
            findings.append(f"missing shared debugger doc: {root / rel}")

    snapshot_file = _snapshot_path(root)
    if not snapshot_file.is_file():
        findings.append(f"missing tool catalog snapshot: {snapshot_file}")
    else:
        try:
            snapshot = _read_json(snapshot_file)
        except ValueError as exc:
            findings.append(str(exc))
            snapshot = {}
        spec_file = tools_root / "spec" / "tool_catalog.json"
        if spec_file.is_file():
            try:
                spec = _read_json(spec_file)
            except ValueError as exc:
                findings.append(str(exc))
                spec = {}
            snapshot_count = int(snapshot.get("tool_count") or 0)
            spec_count = int(spec.get("tool_count") or 0)
            if snapshot_count != spec_count:
                findings.append(f"tool snapshot count mismatch ({snapshot_count} != {spec_count})")
            snapshot_names = {str(item.get("name") or "").strip() for item in snapshot.get("tools", [])}
            spec_names = {str(item.get("name") or "").strip() for item in spec.get("tools", [])}
            if snapshot_names != spec_names:
                findings.append("tool snapshot names differ from package-local tools catalog")
            missing_snapshot_tools = REQUIRED_FRAMEWORK_TOOLS - snapshot_names
            if missing_snapshot_tools:
                findings.append(
                    "framework-required tool missing from snapshot: "
                    + ", ".join(sorted(missing_snapshot_tools))
                )
            missing_spec_tools = REQUIRED_FRAMEWORK_TOOLS - spec_names
            if missing_spec_tools:
                findings.append(
                    "framework-required tool missing from package-local tools source payload catalog: "
                    + ", ".join(sorted(missing_spec_tools))
                )

    if _is_source_root(root):
        try:
            platforms_payload = _read_json(root / "common" / "config" / "platform_capabilities.json")
        except ValueError as exc:
            findings.append(str(exc))
            return findings
        platform_rows = platforms_payload.get("platforms", {})
        target_platforms = [platform] if platform else sorted(platform_rows)
        for platform_name in target_platforms:
            if platform_name not in platform_rows:
                findings.append(f"unknown platform: {platform_name}")
                continue
            for rel in platform_rows.get(platform_name, {}).get("required_paths", []):
                if not (root / rel).exists():
                    findings.append(f"{platform_name}: missing required path: {root / rel}")
    else:
        for rel in ("README.md", "AGENTS.md"):
            if not (root / rel).is_file():
                findings.append(f"missing platform package doc: {root / rel}")

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate fixed debugger binding against the package-local tools/ source payload")
    parser.add_argument("--root", default=str(_default_root()))
    parser.add_argument("--platform", default="", help="Optional platform key when validating the source repo")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when findings exist")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    findings = validate_binding(root, platform=str(args.platform or "").strip())
    if findings:
        print("[binding validation findings]")
        for item in findings:
            print(f" - {item}")
        return 1 if args.strict else 0

    print(f"binding validation passed ({root})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
