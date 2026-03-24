#!/usr/bin/env python3
"""Package-local tool contract validator for runtime hooks."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

TEXT_EXTS = {".md", ".yaml", ".yml", ".json", ".jsonl", ".py", ".toml"}
TOOL_RE = re.compile(r"rd\.[A-Za-z0-9_]+\.[A-Za-z0-9_\.]+")
CALL_RE = re.compile(r"(rd\.[A-Za-z0-9_]+\.[A-Za-z0-9_\.]+)\s*\(([^)]*)\)")
EXPECTED_TOOLS_ROOT = "tools"
EXPECTED_RUNTIME_MODE = "worker_staged"
BANNED_SNIPPETS = {
    "--connect": "legacy CLI connect flag removed; CLI is always daemon-backed",
    "error_message": "use canonical error.message instead of legacy error_message",
    "直接本地 runtime": "framework docs must not describe direct runtime ownership",
    "__CONFIGURE_TOOLS_ROOT__": "legacy configurable tools_root flow removed; use the package-local tools/ source payload",
    "配置 `paths.tools_root`": "legacy manual tools_root configuration removed; use the package-local tools/ source payload",
    "configure `paths.tools_root`": "legacy manual tools_root configuration removed; use the package-local tools/ source payload",
}


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc.msg} (line {exc.lineno}, column {exc.colno}).") from exc


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="ignore")


def _resolve_tools_root(root: Path) -> Path:
    adapter = _read_json(root / "common" / "config" / "platform_adapter.json")
    raw_root = str((adapter.get("paths") or {}).get("tools_source_root", "")).strip()
    if raw_root != EXPECTED_TOOLS_ROOT:
        raise ValueError(
            f"platform_adapter.json must keep paths.tools_source_root='{EXPECTED_TOOLS_ROOT}' and treat tools/ as a package-local source payload"
        )
    runtime_mode = str((adapter.get("runtime") or {}).get("mode", "")).strip()
    if runtime_mode != EXPECTED_RUNTIME_MODE:
        raise ValueError(
            f"platform_adapter.json must keep runtime.mode='{EXPECTED_RUNTIME_MODE}' for daemon-owned worker staging"
        )
    tools_root = (root / EXPECTED_TOOLS_ROOT).resolve()
    required_paths = [
        str(item).strip()
        for item in (adapter.get("validation") or {}).get("required_paths", [])
        if str(item).strip()
    ]
    if not required_paths:
        raise ValueError("platform_adapter.json missing validation.required_paths")
    missing = [rel for rel in required_paths if not (tools_root / rel).is_file()]
    if missing:
        paths = ", ".join(str(tools_root / rel) for rel in missing)
        raise ValueError(f"package-local tools source payload validation failed: missing {paths}")
    return tools_root


def _load_catalog(root: Path) -> tuple[set[str], dict[str, list[dict[str, str]]]]:
    payload = _read_json(_resolve_tools_root(root) / "spec" / "tool_catalog.json")
    names = {str(item.get("name", "")).strip() for item in payload.get("tools", []) if str(item.get("name", "")).strip()}
    prerequisites = {
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
    return names, prerequisites


def _iter_files(root: Path) -> list[Path]:
    bases = [
        root / name
        for name in ("common", "agents", "skills", "hooks", "references", "workflows", ".claude", ".github", ".agents", ".codex")
        if (root / name).exists()
    ]
    files: list[Path] = []
    for base in bases:
        for path in ([base] if base.is_file() else base.rglob("*")):
            if path.is_file() and path.suffix.lower() in TEXT_EXTS:
                files.append(path)
    return files


def _should_scan_banned_snippets(path: Path) -> bool:
    if path.name == "tool_catalog.snapshot.json":
        return False
    if path.suffix.lower() == ".py":
        return False
    return True


def main() -> int:
    root = _root()
    try:
        known_tools, prerequisites = _load_catalog(root)
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 2

    unknown_rows: list[str] = []
    session_rows: list[str] = []
    banned_rows: list[str] = []
    for path in _iter_files(root):
        text = _read_text(path)
        unknown = sorted({ref for ref in set(TOOL_RE.findall(text)) if ref not in known_tools})
        if unknown:
            unknown_rows.append(f"{path}: {', '.join(unknown)}")
        if _should_scan_banned_snippets(path):
            for snippet, reason in BANNED_SNIPPETS.items():
                if snippet in text:
                    banned_rows.append(f"{path}: banned snippet `{snippet}` ({reason})")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for tool, arg_text in CALL_RE.findall(line):
                for prereq in prerequisites.get(tool, []):
                    required = prereq.get("requires", "")
                    when = prereq.get("when", "")
                    if when == "options.remote_id_present" and "remote_id" not in arg_text:
                        continue
                    if required == "session_id" and "session_id" not in arg_text:
                        session_rows.append(f"{path}:{lineno}: {tool}(...) missing session_id prerequisite in example")
                    if required == "capture_file_id" and "capture_file_id" not in arg_text:
                        session_rows.append(f"{path}:{lineno}: {tool}(...) missing capture_file_id prerequisite in example")
                    if required == "remote_id" and ("remote_id" not in arg_text and "options.remote_id" not in arg_text):
                        session_rows.append(f"{path}:{lineno}: {tool}(...) missing remote_id prerequisite in example")

    if unknown_rows or session_rows or banned_rows:
        if unknown_rows:
            print("[unknown rd.* references]")
            for row in unknown_rows:
                print(f" - {row}")
        if session_rows:
            print("[example calls missing prerequisites]")
            for row in session_rows:
                print(f" - {row}")
        if banned_rows:
            print("[banned legacy snippets]")
            for row in banned_rows:
                print(f" - {row}")
        return 1

    print("runtime tool contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
