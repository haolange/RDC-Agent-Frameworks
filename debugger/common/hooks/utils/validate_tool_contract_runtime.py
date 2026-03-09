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
PLACEHOLDER_PREFIX = "__CONFIGURE_"


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="ignore")


def _resolve_tools_root(root: Path) -> Path:
    adapter = _read_json(root / "common" / "config" / "platform_adapter.json")
    raw_root = str((adapter.get("paths") or {}).get("tools_root", "")).strip()
    if not raw_root or raw_root.startswith(PLACEHOLDER_PREFIX):
        raise ValueError("platform_adapter.json missing configured paths.tools_root")
    tools_root = Path(raw_root)
    if not tools_root.is_absolute():
        tools_root = (root / tools_root).resolve()
    required_paths = [str(item).strip() for item in (adapter.get("validation") or {}).get("required_paths", []) if str(item).strip()]
    if not required_paths:
        raise ValueError("platform_adapter.json missing validation.required_paths")
    missing = [rel for rel in required_paths if not (tools_root / rel).is_file()]
    if missing:
        paths = ", ".join(str(tools_root / rel) for rel in missing)
        raise ValueError(f"tools_root validation failed: missing {paths}")
    return tools_root


def _load_catalog(root: Path) -> tuple[set[str], set[str]]:
    payload = _read_json(_resolve_tools_root(root) / "spec" / "tool_catalog.json")
    names = {str(item.get("name", "")).strip() for item in payload.get("tools", []) if str(item.get("name", "")).strip()}
    requires_session = {
        str(item.get("name", "")).strip()
        for item in payload.get("tools", [])
        if "session_id" in {str(param).strip() for param in item.get("param_names", [])}
    }
    return names, requires_session


def _iter_files(root: Path) -> list[Path]:
    bases = [root / name for name in ("common", "agents", "skills", "hooks", "references", "workflows", ".claude", ".github", ".agents", ".codex") if (root / name).exists()]
    files: list[Path] = []
    for base in bases:
        for path in ([base] if base.is_file() else base.rglob("*")):
            if path.is_file() and path.suffix.lower() in TEXT_EXTS:
                files.append(path)
    return files


def main() -> int:
    root = _root()
    try:
        known_tools, requires_session = _load_catalog(root)
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 2

    unknown_rows: list[str] = []
    session_rows: list[str] = []
    for path in _iter_files(root):
        text = _read_text(path)
        unknown = sorted({ref for ref in set(TOOL_RE.findall(text)) if ref not in known_tools})
        if unknown:
            unknown_rows.append(f"{path}: {', '.join(unknown)}")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for tool, arg_text in CALL_RE.findall(line):
                if tool in requires_session and "session_id" not in arg_text:
                    session_rows.append(f"{path}:{lineno}: {tool}(...) missing session_id in example")

    if unknown_rows or session_rows:
        if unknown_rows:
            print("[unknown rd.* references]")
            for row in unknown_rows:
                print(f" - {row}")
        if session_rows:
            print("[example calls missing session_id]")
            for row in session_rows:
                print(f" - {row}")
        return 1

    print("runtime tool contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
