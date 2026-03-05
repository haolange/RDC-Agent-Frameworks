#!/usr/bin/env python3
"""Sync platform agent prompts from common/agents SSOT."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List


COMMON_ORDER = [
    "01_team_lead.md",
    "02_triage_taxonomy.md",
    "03_capture_repro.md",
    "04_pass_graph_pipeline.md",
    "05_pixel_value_forensics.md",
    "06_shader_ir.md",
    "07_driver_device.md",
    "08_skeptic.md",
    "09_report_knowledge_curator.md",
]

CLAUDE_WORK_NAMES = {
    "01_team_lead.md": "team_lead.md",
    "02_triage_taxonomy.md": "triage.md",
    "03_capture_repro.md": "capture.md",
    "04_pass_graph_pipeline.md": "pipeline.md",
    "05_pixel_value_forensics.md": "forensics.md",
    "06_shader_ir.md": "shader.md",
    "07_driver_device.md": "driver.md",
    "08_skeptic.md": "skeptic.md",
    "09_report_knowledge_curator.md": "curator.md",
}

META = {
    "01_team_lead.md": ("Debugger Team Lead / Orchestrator", "Coordinate delegates and enforce quality gates", "#E74C3C"),
    "02_triage_taxonomy.md": ("Debugger Triage & Taxonomy", "Classify symptoms and propose initial SOP", "#8E44AD"),
    "03_capture_repro.md": ("Debugger Capture & Repro", "Capture A/B evidence and anchor the failing event", "#2ECC71"),
    "04_pass_graph_pipeline.md": ("Debugger Pass Graph / Pipeline", "Trace event divergence through render passes", "#3498DB"),
    "05_pixel_value_forensics.md": ("Debugger Pixel Value Forensics", "Locate first bad event using pixel evidence", "#1ABC9C"),
    "06_shader_ir.md": ("Debugger Shader & IR", "Analyze shader source/disassembly/debug state", "#9B59B6"),
    "07_driver_device.md": ("Debugger Driver & Device", "Perform cross-device attribution and API/ISA checks", "#F39C12"),
    "08_skeptic.md": ("Debugger Skeptic / Adversarial Reviewer", "Challenge weak claims and sign off only when proven", "#C0392B"),
    "09_report_knowledge_curator.md": ("Debugger Report & Knowledge Curator", "Produce BugFull/BugCard and curate reusable knowledge", "#16A085"),
}

AGENT_IDS = {
    "01_team_lead.md": "team_lead",
    "02_triage_taxonomy.md": "triage_agent",
    "03_capture_repro.md": "capture_repro_agent",
    "04_pass_graph_pipeline.md": "pass_graph_pipeline_agent",
    "05_pixel_value_forensics.md": "pixel_forensics_agent",
    "06_shader_ir.md": "shader_ir_agent",
    "07_driver_device.md": "driver_device_agent",
    "08_skeptic.md": "skeptic_agent",
    "09_report_knowledge_curator.md": "curator_agent",
}


def _root() -> Path:
    # .../extensions/debugger/scripts/sync_platform_agents.py
    return Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _frontmatter_claude_code(name: str, desc: str, color: str, agent_id: str) -> str:
    return "\n".join(
        [
            "---",
            f'name: "{name}"',
            f'description: "{desc}"',
            f'agent_id: "{agent_id}"',
            'model: "claude-sonnet-4-5"',
            'tools: "bash,read"',
            f'color: "{color}"',
            "---",
        ],
    )


def _frontmatter_code_buddy(name: str, desc: str, color: str, agent_id: str) -> str:
    return "\n".join(
        [
            "---",
            f'name: "{name}"',
            f'description: "{desc}"',
            f'agent_id: "{agent_id}"',
            "model: inherit",
            "tools: Bash,Read,Write",
            "skills: debugger",
            f'color: "{color}"',
            "---",
        ],
    )


def _frontmatter_copilot(name: str, desc: str, color: str, agent_id: str) -> str:
    return "\n".join(
        [
            "---",
            f'name: "{name}"',
            f'description: "{desc}"',
            f'agent_id: "{agent_id}"',
            'model: "claude-sonnet-4-5"',
            'tools: ["bash", "read"]',
            f'color: "{color}"',
            "---",
        ],
    )


def _frontmatter_claude_work(name: str, desc: str, color: str, agent_id: str) -> str:
    return "\n".join(
        [
            "---",
            f'name: "{name}"',
            f'description: "{desc}"',
            f'agent_id: "{agent_id}"',
            'tools: ["bash","read"]',
            f'color: "{color}"',
            "---",
        ],
    )


def _wrap(frontmatter: str, body: str) -> str:
    return (
        f"{frontmatter}\n\n"
        "<!-- Auto-generated from common/agents by scripts/sync_platform_agents.py. Do not edit platform copies manually. -->\n\n"
        f"{body.strip()}\n"
    )


def _sync_indexed_platform(target_dir: Path, frontmatter_builder) -> None:
    common_dir = _root() / "common" / "agents"
    for filename in COMMON_ORDER:
        src = common_dir / filename
        if not src.is_file():
            raise FileNotFoundError(f"missing source agent: {src}")
        name, desc, color = META[filename]
        agent_id = AGENT_IDS[filename]
        body = _read(src)
        fm = frontmatter_builder(name, desc, color, agent_id)
        _write(target_dir / filename, _wrap(fm, body))


def _sync_claude_work(target_dir: Path) -> None:
    common_dir = _root() / "common" / "agents"
    for filename in COMMON_ORDER:
        src = common_dir / filename
        if not src.is_file():
            raise FileNotFoundError(f"missing source agent: {src}")
        name, desc, color = META[filename]
        agent_id = AGENT_IDS[filename]
        dst_name = CLAUDE_WORK_NAMES[filename]
        body = _read(src)
        fm = _frontmatter_claude_work(name, desc, color, agent_id)
        _write(target_dir / dst_name, _wrap(fm, body))


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync platform agent prompts from common/agents")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only print planned targets (no writes)",
    )
    args = parser.parse_args()

    root = _root()
    targets = [
        root / "platforms" / "claude-code" / "agents",
        root / "platforms" / "code-buddy" / "agents",
        root / "platforms" / "copilot" / "agents",
        root / "platforms" / "claude-work" / "agents",
    ]

    if args.check:
        print("planned targets:")
        for item in targets:
            print(f"  - {item}")
        return 0

    _sync_indexed_platform(targets[0], _frontmatter_claude_code)
    _sync_indexed_platform(targets[1], _frontmatter_code_buddy)
    _sync_indexed_platform(targets[2], _frontmatter_copilot)
    _sync_claude_work(targets[3])
    print("platform agent sync complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
