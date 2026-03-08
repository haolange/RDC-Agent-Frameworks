#!/usr/bin/env python3
"""Validate debugger platform template layout contracts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "common" / "config" / "platform_capabilities.json"
TEXT_EXTS = {".json", ".jsonl", ".md", ".toml", ".txt", ".yaml", ".yml"}
FORBIDDEN_DIRS = ("common", "docs", "scripts")
FORBIDDEN_COPY_TEXT = (
    re.compile(r"README\.copy-common"),
    re.compile(r"先将根目录.*common.*复制"),
    re.compile(r"复制到当前模板根"),
    re.compile(r"拷入平台根"),
)
FORBIDDEN_RUNTIME_REFS = (
    re.compile(r"(?<!common/)docs/cli-mode-reference\.md"),
    re.compile(r"(?<!common/)docs/model-routing\.md"),
    re.compile(r"(?<!common/)docs/platform-capability-matrix\.md"),
    re.compile(r"(?<!common/)docs/platform-capability-model\.md"),
    re.compile(r"(?<!common/)docs/runtime-coordination-model\.md"),
)


@dataclass(frozen=True)
class PlatformRule:
    key: str
    required_files: tuple[str, ...]


def load_rules() -> tuple[PlatformRule, ...]:
    payload = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    return tuple(
        PlatformRule(key=key, required_files=tuple(row["required_paths"]))
        for key, row in payload["platforms"].items()
    )


def iter_text_files(base: Path) -> list[Path]:
    if not base.exists():
        return []
    return [path for path in base.rglob("*") if path.is_file() and path.suffix.lower() in TEXT_EXTS]


def validate_root_state() -> list[str]:
    findings: list[str] = []
    for root_artifact in (ROOT / ".claude", ROOT / ".github", ROOT / ".codex", ROOT / ".agents"):
        if root_artifact.exists():
            findings.append(f"source root must not contain host artifact: {root_artifact}")
    return findings


def validate_platform(rule: PlatformRule) -> list[str]:
    findings: list[str] = []
    package_root = ROOT / "platforms" / rule.key

    for rel_path in rule.required_files:
        full_path = ROOT / rel_path
        if not full_path.exists():
            findings.append(f"{rule.key}: missing required file {full_path}")

    for rel_dir in FORBIDDEN_DIRS:
        full_path = package_root / rel_dir
        if full_path.exists():
            findings.append(f"{rule.key}: forbidden copied shared content {full_path}")

    for file_path in iter_text_files(package_root):
        text = file_path.read_text(encoding="utf-8-sig", errors="ignore")
        for marker in FORBIDDEN_COPY_TEXT:
            match = marker.search(text)
            if match:
                findings.append(f"{rule.key}: forbidden copy-era text in {file_path}: {match.group(0)}")
        for marker in FORBIDDEN_RUNTIME_REFS:
            match = marker.search(text)
            if match:
                findings.append(
                    f"{rule.key}: forbidden maintainer-doc runtime reference in {file_path}: {match.group(0)}"
                )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate debugger platform layout")
    parser.add_argument("--strict", action="store_true", help="Return non-zero on findings")
    args = parser.parse_args()

    findings = validate_root_state()
    for rule in load_rules():
        findings.extend(validate_platform(rule))

    if findings:
        print("[platform layout findings]")
        for row in findings:
            print(f"  - {row}")
        return 1 if args.strict else 0

    print("platform layout validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
