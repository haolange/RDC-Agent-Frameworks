#!/usr/bin/env python3
"""Sync platform agent prompts from common/agents SSOT."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

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

COPILOT_IDE_NAMES = {
    "01_team_lead.md": "orchestrator.md",
    "02_triage_taxonomy.md": "triage.md",
    "03_capture_repro.md": "capture.md",
    "04_pass_graph_pipeline.md": "pipeline.md",
    "05_pixel_value_forensics.md": "forensics.md",
    "06_shader_ir.md": "shader.md",
    "07_driver_device.md": "driver.md",
    "08_skeptic.md": "verifier.md",
    "09_report_knowledge_curator.md": "report-curator.md",
}

META = {
    "01_team_lead.md": ("RenderDoc/RDC Orchestrator", "Coordinate the GPU debug workflow and enforce verdict gates", "#E74C3C"),
    "02_triage_taxonomy.md": ("RenderDoc/RDC Triage", "Normalize symptoms, triggers, and SOP entrypoints", "#8E44AD"),
    "03_capture_repro.md": ("RenderDoc/RDC Capture", "Establish reproducible captures and anchors", "#2ECC71"),
    "04_pass_graph_pipeline.md": ("RenderDoc/RDC Pipeline", "Trace pass divergence and dependency chains", "#3498DB"),
    "05_pixel_value_forensics.md": ("RenderDoc/RDC Forensics", "Locate the first bad event by pixel evidence", "#1ABC9C"),
    "06_shader_ir.md": ("RenderDoc/RDC Shader", "Analyze shader source, IR, and suspicious fingerprints", "#9B59B6"),
    "07_driver_device.md": ("RenderDoc/RDC Driver", "Perform cross-device attribution and platform checks", "#F39C12"),
    "08_skeptic.md": ("RenderDoc/RDC Verifier", "Challenge weak claims and sign off only when proven", "#C0392B"),
    "09_report_knowledge_curator.md": ("RenderDoc/RDC Curator", "Produce reports and merge reusable GPU debug knowledge", "#16A085"),
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

COPILOT_IDE_TOOLS = [
    "changes",
    "codebase",
    "editFiles",
    "extensions",
    "fetch",
    "findTestFiles",
    "githubRepo",
    "problems",
    "runCommands",
    "runTasks",
    "search",
    "searchResults",
    "testFailure",
    "terminalLastCommand",
    "terminalSelection",
    "usages",
]


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_model_map() -> dict:
    config_path = _root() / "common" / "config" / "model_routing.json"
    return _load_json(config_path)["platform_mappings"]


def _load_capabilities() -> dict:
    config_path = _root() / "common" / "config" / "platform_capabilities.json"
    return _load_json(config_path)["platforms"]


def _frontmatter_for(platform_key: str, name: str, desc: str, color: str, agent_id: str) -> str:
    model = _load_model_map()[platform_key][agent_id]
    if platform_key == "claude-code":
        return "\n".join([
            "---",
            f'name: "{name}"',
            f'description: "{desc}"',
            f'agent_id: "{agent_id}"',
            f'model: "{model}"',
            'tools: "bash,read"',
            f'color: "{color}"',
            "---",
        ])
    if platform_key == "code-buddy":
        return "\n".join([
            "---",
            f'name: "{name}"',
            f'description: "{desc}"',
            f'agent_id: "{agent_id}"',
            f'model: "{model}"',
            "tools: Bash,Read,Write",
            "skills: renderdoc-rdc-gpu-debug",
            f'color: "{color}"',
            "---",
        ])
    if platform_key == "copilot-cli":
        return "\n".join([
            "---",
            f'name: "{name}"',
            f'description: "{desc}"',
            f'agent_id: "{agent_id}"',
            f'model: "{model}"',
            'tools: ["bash", "read", "write"]',
            "skills: renderdoc-rdc-gpu-debug",
            f'color: "{color}"',
            "---",
        ])
    if platform_key == "claude-work":
        return "\n".join([
            "---",
            f'name: "{name}"',
            f'description: "{desc}"',
            f'agent_id: "{agent_id}"',
            f'model: "{model}"',
            'tools: ["bash", "read"]',
            f'color: "{color}"',
            "---",
        ])
    if platform_key == "copilot-ide":
        return "\n".join([
            "---",
            f'description: "{desc}."',
            f'tools: {json.dumps(COPILOT_IDE_TOOLS)}',
            f'model: "{model}"',
            "---",
        ])
    raise KeyError(platform_key)


def _wrap(platform_key: str, frontmatter: str, heading: str, body: str) -> str:
    if platform_key == "copilot-ide":
        return (
            f"{frontmatter}\n\n"
            "<!-- Auto-generated from common/agents by scripts/sync_platform_agents.py. Do not edit platform copies manually. -->\n\n"
            f"# {heading}\n\n"
            "Use RenderDoc/RDC platform tools to debug GPU rendering issues.\n\n"
            f"{body.strip()}\n"
        )
    return (
        f"{frontmatter}\n\n"
        "<!-- Auto-generated from common/agents by scripts/sync_platform_agents.py. Do not edit platform copies manually. -->\n\n"
        f"{body.strip()}\n"
    )


def _sync_indexed_platform(platform_key: str, target_dir: Path) -> None:
    common_dir = _root() / "common" / "agents"
    for filename in COMMON_ORDER:
        src = common_dir / filename
        if not src.is_file():
            raise FileNotFoundError(f"missing source agent: {src}")
        name, desc, color = META[filename]
        agent_id = AGENT_IDS[filename]
        body = _read(src)
        fm = _frontmatter_for(platform_key, name, desc, color, agent_id)
        _write(target_dir / filename, _wrap(platform_key, fm, name, body))


def _sync_named_platform(platform_key: str, target_dir: Path, names: dict[str, str]) -> None:
    common_dir = _root() / "common" / "agents"
    for filename in COMMON_ORDER:
        src = common_dir / filename
        if not src.is_file():
            raise FileNotFoundError(f"missing source agent: {src}")
        name, desc, color = META[filename]
        agent_id = AGENT_IDS[filename]
        body = _read(src)
        fm = _frontmatter_for(platform_key, name, desc, color, agent_id)
        _write(target_dir / names[filename], _wrap(platform_key, fm, name, body))


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync platform agent prompts from common/agents")
    parser.add_argument("--check", action="store_true", help="Only print planned targets (no writes)")
    args = parser.parse_args()

    root = _root()
    capabilities = _load_capabilities()
    targets = []
    if capabilities["claude-code"]["custom_agents"]:
        targets.append(("claude-code", root / "platforms" / "claude-code" / "agents"))
    if capabilities["code-buddy"]["custom_agents"]:
        targets.append(("code-buddy", root / "platforms" / "code-buddy" / "agents"))
    if capabilities["copilot-cli"]["custom_agents"]:
        targets.append(("copilot-cli", root / "platforms" / "copilot-cli" / "agents"))
    if capabilities["claude-work"]["custom_agents"]:
        targets.append(("claude-work", root / "platforms" / "claude-work" / "agents"))
    if capabilities["copilot-ide"]["custom_agents"]:
        targets.append(("copilot-ide", root / "platforms" / "copilot-ide" / ".github" / "agents"))

    if args.check:
        print("planned targets:")
        for platform_key, item in targets:
            print(f"  - {platform_key}: {item}")
        return 0

    _sync_indexed_platform("claude-code", root / "platforms" / "claude-code" / "agents")
    _sync_indexed_platform("code-buddy", root / "platforms" / "code-buddy" / "agents")
    _sync_indexed_platform("copilot-cli", root / "platforms" / "copilot-cli" / "agents")
    _sync_named_platform("claude-work", root / "platforms" / "claude-work" / "agents", CLAUDE_WORK_NAMES)
    _sync_named_platform("copilot-ide", root / "platforms" / "copilot-ide" / ".github" / "agents", COPILOT_IDE_NAMES)
    print("platform agent sync complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
