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
TOOL_RE = re.compile(r"rd\.[A-Za-z0-9_]+\.[A-Za-z0-9_\.]+")
CALL_RE = re.compile(r"(rd\.[A-Za-z0-9_]+\.[A-Za-z0-9_\.]+)\s*\(([^)]*)\)")
ENV_CATALOG = "DEBUGGER_PLATFORM_CATALOG"
PLACEHOLDER_PREFIX = "__CONFIGURE_"
SNAPSHOT_PATH = Path("common") / "config" / "tool_catalog.snapshot.json"


@dataclass
class Findings:
 unknown_tools: dict[str, set[str]] = field(default_factory=dict)
 missing_session_examples: list[str] = field(default_factory=list)
 def has_issues(self): return any([self.unknown_tools, self.missing_session_examples])


def root():
 return Path(__file__).resolve().parents[1]


def is_source_root(cur):
 return (cur / "platforms").is_dir()


def path_base(cur):
 return cur.parent if is_source_root(cur) else cur


def read_json(path):
 return json.loads(path.read_text(encoding="utf-8-sig"))


def adapter_payload(cur):
 return read_json(cur / "common" / "config" / "platform_adapter.json")


def resolve_tools_root(cur):
 payload = adapter_payload(cur)
 raw_root = str(payload.get("paths", {}).get("tools_root", "")).strip()
 if not raw_root or raw_root.startswith(PLACEHOLDER_PREFIX):
  raise ValueError("platform_adapter.json missing configured paths.tools_root")
 candidate = Path(raw_root)
 tools_root = candidate if candidate.is_absolute() else (path_base(cur) / candidate).resolve()
 required_paths = [str(item).strip() for item in payload.get("validation", {}).get("required_paths", []) if str(item).strip()]
 if not required_paths:
  raise ValueError("platform_adapter.json missing validation.required_paths")
 missing = [rel for rel in required_paths if not (tools_root / rel).is_file()]
 if missing:
  missing_paths = ", ".join(str(tools_root / rel) for rel in missing)
  raise ValueError(f"tools_root validation failed: missing {missing_paths}")
 return tools_root


def default_catalog(cur):
 env_override = os.environ.get(ENV_CATALOG, "").strip()
 if env_override:
  return Path(env_override).resolve()
 return (resolve_tools_root(cur) / "spec" / "tool_catalog.json").resolve()


def source_snapshot(cur):
 return (cur / SNAPSHOT_PATH).resolve()


def load_catalog(path):
 payload = read_json(path)
 names = {str(item.get("name", "")).strip() for item in payload.get("tools", []) if str(item.get("name", "")).strip()}
 requires_session = {str(item.get("name", "")).strip() for item in payload.get("tools", []) if "session_id" in {str(param).strip() for param in item.get("param_names", [])}}
 return names, requires_session


def iter_scan_files(cur):
 roots = [cur / "common", cur / "platforms"] if is_source_root(cur) else [cur] + [cur / name for name in ("common", "docs", "scripts", "agents", "skills", "hooks", "references", "workflows", ".claude", ".github") if (cur / name).exists()]
 return [path for base in roots for path in ([base] if base.is_file() else base.rglob("*")) if path.is_file() and path.suffix.lower() in TEXT_EXTS and "design" not in path.parts]


def read_text(path):
 return path.read_text(encoding="utf-8-sig", errors="ignore")


def check_unknown_tools(files, known_tools):
 return {str(path): {ref for ref in set(TOOL_RE.findall(read_text(path))) if ref not in known_tools} for path in files if {ref for ref in set(TOOL_RE.findall(read_text(path))) if ref not in known_tools}}


def check_session_examples(files, requires_session):
 return [f"{path}:{lineno}: {tool}(...) missing session_id in example" for path in files for lineno, line in enumerate(read_text(path).splitlines(), start=1) for tool, arg_text in CALL_RE.findall(line) if tool in requires_session and "session_id" not in arg_text]


def print_findings(findings):
 if findings.unknown_tools: print("[unknown rd.* references]"); [print(" - " + file_path + ": " + ", ".join(sorted(findings.unknown_tools[file_path]))) for file_path in sorted(findings.unknown_tools)]
 if findings.missing_session_examples: print("[example calls missing session_id]"); [print(" - " + row) for row in findings.missing_session_examples]


def main():
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
 except Exception as exc: print(str(exc)); return 2
 if not catalog.is_file(): print(f"catalog not found: {catalog}"); return 2
 known_tools, requires_session = load_catalog(catalog)
 files = iter_scan_files(cur)
 findings = Findings(check_unknown_tools(files, known_tools), check_session_examples(files, requires_session))
 if findings.has_issues(): print_findings(findings); return 1 if args.strict else 0
 print(f"tool contract validation passed ({catalog})")
 return 0


if __name__ == "__main__":
 sys.exit(main())
