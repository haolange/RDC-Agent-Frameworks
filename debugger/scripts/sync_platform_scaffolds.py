#!/usr/bin/env python3
"""Render thin platform workspaces from debugger/common/ SSOT."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / "common"
COMMON_AGENTS = COMMON / "agents"
COMMON_SKILL = COMMON / "skills" / "renderdoc-rdc-gpu-debug" / "SKILL.md"
CONFIG = COMMON / "config"


@dataclass(frozen=True)
class PlatformSpec:
    key: str
    managed_dirs: tuple[str, ...]
    managed_files: tuple[str, ...] = ()


SPECS = (
    PlatformSpec("claude-code", managed_dirs=(".claude",), managed_files=("README.md",)),
    PlatformSpec(
        "code-buddy",
        managed_dirs=(".codebuddy-plugin", "agents", "skills", "hooks"),
        managed_files=("README.md", ".mcp.json"),
    ),
    PlatformSpec(
        "copilot-cli",
        managed_dirs=("agents", "skills", "hooks"),
        managed_files=("README.md", ".mcp.json", ".copilot-plugin.json"),
    ),
    PlatformSpec(
        "copilot-ide",
        managed_dirs=(".github", "references"),
        managed_files=("README.md", "agent-plugin.json"),
    ),
    PlatformSpec(
        "claude-desktop",
        managed_dirs=("references",),
        managed_files=("README.md", "claude_desktop_config.json"),
    ),
    PlatformSpec("manus", managed_dirs=("references", "workflows"), managed_files=("README.md",)),
    PlatformSpec("codex", managed_dirs=(".agents", ".codex"), managed_files=("README.md", "AGENTS.md")),
)

FORBIDDEN_DIRS = ("common", "docs", "scripts")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


ROLE_MANIFEST = read_json(CONFIG / "role_manifest.json")
ROLE_POLICY = read_json(CONFIG / "role_policy.json")
MODEL_ROUTING = read_json(CONFIG / "model_routing.json")
MCP_SERVERS = read_json(CONFIG / "mcp_servers.json")
PLATFORM_TARGETS = read_json(CONFIG / "platform_targets.json")
PLATFORM_CAPS = read_json(CONFIG / "platform_capabilities.json")


def normalize(text: str) -> str:
    return text.rstrip() + "\n"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalize(text), encoding="utf-8")


def rel_path(from_file: Path, target: Path) -> str:
    return Path(os.path.relpath(target, start=from_file.parent)).as_posix()


def package_root(platform_key: str) -> Path:
    return ROOT / "platforms" / platform_key


def roles() -> list[dict]:
    return ROLE_MANIFEST["roles"]


def role_by_id(agent_id: str) -> dict:
    for role in roles():
        if role["agent_id"] == agent_id:
            return role
    raise KeyError(agent_id)


def platform_model(platform_key: str, agent_id: str) -> str:
    profile_name = MODEL_ROUTING["role_profiles"][agent_id]
    return MODEL_ROUTING["profiles"][profile_name]["platform_rendering"][platform_key]


def role_style(agent_id: str) -> dict:
    profile_name = ROLE_POLICY["roles"][agent_id]["model_profile"]
    return ROLE_POLICY["model_profiles"][profile_name]


def role_targets(platform_key: str, agent_id: str) -> list[str]:
    policy = ROLE_POLICY["roles"][agent_id]
    targets = []
    for target_id in policy["delegates_to"]:
        target_role = role_by_id(target_id)
        file_name = target_role["platform_files"].get(platform_key)
        if file_name is None:
            continue
        targets.append(Path(file_name).stem)
    return targets


def readme(platform_key: str) -> str:
    caps = PLATFORM_CAPS["platforms"][platform_key]
    target = PLATFORM_TARGETS["platforms"][platform_key]
    surfaces = ", ".join(target["native_surfaces"])
    return f"""# {caps['display_name']} Template

当前目录是 {caps['display_name']} 的 direct-reference workspace 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

约束：

- 本目录直接引用仓库中的共享 `debugger/common/`，禁止复制或镜像 `common/` 内容。
- 当前平台状态：`{caps['status_label']}`。
- 当前平台生成面：`{surfaces}`。
- 共享模型、delegation、hook、MCP 与入口布局全部来自 `common/config/` 和 `debugger/scripts/sync_platform_scaffolds.py`。
"""


def shared_read_order(path: Path, role_prompt: Path) -> str:
    return "\n".join(
        [
            "按顺序阅读：",
            "",
            f"1. `{rel_path(path, COMMON / 'AGENT_CORE.md')}`",
            f"2. `{rel_path(path, role_prompt)}`",
            f"3. `{rel_path(path, COMMON_SKILL)}`",
        ]
    )


def agent_body(platform_key: str, role: dict, target_file: Path) -> str:
    role_prompt = COMMON / role["source_prompt"]
    return f"""# RenderDoc/RDC Agent Wrapper

当前文件是 {PLATFORM_CAPS['platforms'][platform_key]['display_name']} 宿主入口。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

本文件只引用共享 `common/` 正文，不得复制或改写角色职责。

{shared_read_order(target_file, role_prompt)}
"""


def code_buddy_agent(role: dict, target_file: Path) -> str:
    frontmatter = yaml_block(
        {
            "agent_id": role["agent_id"],
            "category": role["category"],
            "model": platform_model("code-buddy", role["agent_id"]),
            "delegates_to": ROLE_POLICY["roles"][role["agent_id"]]["delegates_to"],
        }
    )
    return f"""{frontmatter}

{agent_body("code-buddy", role, target_file)}
"""


def yaml_block(values: dict[str, object]) -> str:
    rows: list[str] = ["---"]
    for key, value in values.items():
        if value in (None, "", [], {}):
            continue
        if isinstance(value, list):
            rows.append(f"{key}:")
            for item in value:
                rows.append(f"  - {item}")
        else:
            rows.append(f'{key}: "{value}"')
    rows.append("---")
    return "\n".join(rows)


def claude_code_agent(role: dict, target_file: Path) -> str:
    frontmatter = yaml_block({"description": role["description"], "model": platform_model("claude-code", role["agent_id"])})
    return f"""{frontmatter}

{agent_body("claude-code", role, target_file)}
"""


def copilot_ide_agent(role: dict, target_file: Path) -> str:
    frontmatter = yaml_block(
        {
            "description": role["description"],
            "model": platform_model("copilot-ide", role["agent_id"]),
            "handoffs": role_targets("copilot-ide", role["agent_id"]),
        }
    )
    return f"""{frontmatter}

{agent_body("copilot-ide", role, target_file)}
"""


def copilot_cli_agent(role: dict, target_file: Path) -> str:
    frontmatter = yaml_block({"description": role["description"]})
    return f"""{frontmatter}

{agent_body("copilot-cli", role, target_file)}
"""


def skill_wrapper(platform_key: str, target_file: Path) -> str:
    common_caps = rel_path(target_file, CONFIG / "platform_capabilities.json")
    return f"""# RenderDoc/RDC GPU Debug Skill Wrapper

当前文件是 {PLATFORM_CAPS['platforms'][platform_key]['display_name']} 的 skill 入口。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

共享 skill 入口：

- `{rel_path(target_file, COMMON_SKILL)}`
- `coordination_mode` 与降级边界以 `{common_caps}` 的当前平台定义为准。
"""


def claude_code_entry(target_file: Path) -> str:
    return f"""# Claude Code Entry

当前目录是 Claude Code direct-reference 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

先阅读：

1. `{rel_path(target_file, COMMON / 'AGENT_CORE.md')}`
2. `{rel_path(target_file, COMMON_SKILL)}`
3. `{rel_path(target_file, COMMON / 'docs' / 'platform-capability-model.md')}`
"""


def copilot_instructions(target_file: Path) -> str:
    return f"""# Copilot IDE Instructions

当前目录是 Copilot IDE / VS Code 的 direct-reference 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

先阅读：

1. `{rel_path(target_file, COMMON / 'AGENT_CORE.md')}`
2. `{rel_path(target_file, COMMON_SKILL)}`
3. `{rel_path(target_file, COMMON / 'docs' / 'platform-capability-model.md')}`
4. `../references/entrypoints.md`
"""


def references_entry(platform_key: str, target_file: Path) -> str:
    host = PLATFORM_CAPS["platforms"][platform_key]["display_name"]
    return f"""# {host} Entrypoints

当前目录只提供宿主入口提示；运行时共享文档统一直接引用仓库中的 `debugger/common/`。

先阅读：

1. `{rel_path(target_file, COMMON / 'AGENT_CORE.md')}`
2. `{rel_path(target_file, COMMON / 'docs' / 'platform-capability-model.md')}`
3. `{rel_path(target_file, COMMON_SKILL)}`
"""


def manus_workflow() -> str:
    return """# RenderDoc/RDC GPU Debug Workflow

## 目标

在低能力宿主中，用 workflow 方式完成 RenderDoc/RDC GPU Debug 的最小闭环。

## 阶段

1. `triage`
   - 结构化现象、触发条件、可能的 SOP 入口
2. `capture/session`
   - 确认 `.rdc`、session、frame、event anchor
3. `specialist analysis`
   - 从 pipeline、forensics、shader、driver 四个方向收集证据
4. `skeptic`
   - 复核证据链是否足以支持结论
5. `curation`
   - 生成 BugFull / BugCard，写入 session artifacts

## workflow 约束

- Manus 不承担 custom agents / per-agent model 的宿主能力。
- workflow 的每一阶段都必须引用共享 artifact contract。
- `workflow_stage` 是该平台的协作上限，不模拟 team-agent 实时协作。
- remote 阶段由单一 runtime owner 顺序完成 `rd.remote.connect -> rd.remote.ping -> rd.capture.open_file -> rd.capture.open_replay -> re-anchor -> collect evidence`。
- 若需要跨轮次继续调查，必须依赖可重建的 `runtime_baton`，不得凭记忆续跑 live runtime。
- 如需动态 tool discovery，应停止 workflow 并切回支持 `MCP` 的平台。
"""


def mcp_payload() -> dict:
    payload = {"servers": {}}
    for name, server in MCP_SERVERS["servers"].items():
        payload["servers"][name] = {
            "command": server["command"],
            "args": server["args"],
        }
    return payload


def code_buddy_plugin() -> dict:
    return {
        "name": "renderdoc-rdc-gpu-debug-agent",
        "description": "RenderDoc/RDC GPU Debug 的 Code Buddy 参考实现，直接引用共享 common 并生成 hooks、skills、agents 与 MCP。",
        "author": {"name": "RenderDoc/RDC GPU Debug"},
        "keywords": ["renderdoc", "rdc", "gpu", "debug", "mcp", "agent"],
        "agents": "./agents/",
        "skills": "./skills/",
        "hooks": "./hooks/hooks.json",
        "mcpServers": "./.mcp.json",
    }


def copilot_cli_plugin() -> dict:
    return {
        "name": "renderdoc-rdc-gpu-debug",
        "description": "Use RenderDoc/RDC platform tools to debug GPU rendering captures through direct-reference agents, skills, hooks, and MCP.",
        "author": {"name": "RenderDoc/RDC GPU Debug"},
        "keywords": ["renderdoc", "rdc", "gpu", "debug", "mcp", "capture"],
        "agents": "./agents/",
        "skills": "./skills/",
        "hooks": "./hooks/hooks.json",
        "mcpServers": "./.mcp.json",
    }


def code_buddy_hooks() -> dict:
    base = "${CODEBUDDY_PLUGIN_ROOT}/../../common/hooks/utils/codebuddy_hook_dispatch.py"
    return {
        "PostToolUse": [
            {
                "matcher": "Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": f'uv run --with pyyaml python "{base}" write-bugcard',
                        "description": "BugCard contract and schema validation",
                        "timeout": 30000,
                    }
                ],
            },
            {
                "matcher": "Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": f'uv run --with pyyaml python "{base}" write-skeptic',
                        "description": "Skeptic signoff artifact validation",
                        "timeout": 30000,
                    }
                ],
            },
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": f'uv run --with pyyaml python "{base}" stop-gate',
                        "description": "Finalization gate: causal anchor + counterfactual + skeptic + session artifacts",
                        "timeout": 30000,
                    }
                ]
            }
        ],
    }


def copilot_cli_hooks() -> dict:
    base = "../../common/hooks/utils/codebuddy_hook_dispatch.py"
    return {
        "PostToolUse": [
            {
                "matcher": "Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": f"uv run --with pyyaml python {base} write-bugcard",
                        "description": "Validate BugCard before write",
                    }
                ],
            },
            {
                "matcher": "Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": f"uv run --with pyyaml python {base} write-skeptic",
                        "description": "Validate skeptic signoff artifact",
                    }
                ],
            },
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": f"uv run --with pyyaml python {base} stop-gate",
                        "description": "Finalization gate",
                    }
                ]
            }
        ],
    }


def claude_code_settings() -> dict:
    base = "../../common/hooks/utils/codebuddy_hook_dispatch.py"
    return {
        "description": "RenderDoc/RDC GPU Debug - Claude Code direct-reference adaptation",
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": {"tool_name": "Write", "file_pattern": "**/knowledge/library/**/*bugcard*.yaml"},
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"uv run --with pyyaml python {base} write-bugcard",
                            "description": "Validate tool contract and BugCard schema before library write",
                            "on_failure": "block",
                            "failure_message": "BugCard write blocked: tool contract drift or schema validation failed.",
                        }
                    ],
                },
                {
                    "matcher": {
                        "tool_name": "Write",
                        "file_pattern": "**/knowledge/library/sessions/**/skeptic_signoff.yaml",
                    },
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"uv run --with pyyaml python {base} write-skeptic",
                            "description": "Validate skeptic signoff artifact format",
                            "on_failure": "warn",
                            "failure_message": "Skeptic signoff file did not pass validation.",
                        }
                    ],
                },
            ],
            "Stop": [
                {
                    "matcher": {"assistant_message_pattern": ".*"},
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"uv run --with pyyaml python {base} stop-gate",
                            "description": "Finalization gate for RenderDoc/RDC GPU Debug (causal anchor + counterfactual + skeptic)",
                            "on_failure": "block",
                            "failure_message": "Finalization blocked by session artifact or contract checks.",
                        }
                    ],
                }
            ],
        },
        "mcpServers": {
            name: {"command": server["command"], "args": server["args"]}
            for name, server in MCP_SERVERS["servers"].items()
        },
    }


def copilot_ide_plugin() -> dict:
    return {
        "name": "renderdoc-rdc-gpu-debug-ide",
        "description": "RenderDoc/RDC GPU Debug 的 Copilot IDE direct-reference 适配包。",
        "agentsRoot": ".github/agents",
        "notes": [
            "Use preferred per-agent models where the IDE host supports them.",
            "Preserve role routing and evidence gates even when the host ignores model preference.",
            "Read references/entrypoints.md before attempting a CLI-style flow inside the IDE host.",
        ],
    }


def claude_desktop_config() -> dict:
    return {
        "mcpServers": {
            name: {
                "command": server["command"],
                "args": server["args"],
            }
            for name, server in MCP_SERVERS["servers"].items()
        }
    }


def codex_readme() -> str:
    return """# Codex Template

当前目录是 Codex 的 workspace-native direct-reference 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

约束：

- 打开当前目录作为 Codex workspace root。
- 宿主入口由 `AGENTS.md`、`.agents/skills/`、`.codex/config.toml` 和 `.codex/agents/*.toml` 共同构成。
- `multi_agent` 当前按 experimental / CLI-first 理解，但共享规则与 role config 已完整生成。
"""


def codex_agents_md(target_file: Path) -> str:
    lines = [
        "# Codex Workspace Instructions",
        "",
        "当前目录是 Codex workspace-native 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。",
        "",
        "先阅读：",
        "",
        f"1. `{rel_path(target_file, COMMON / 'AGENT_CORE.md')}`",
        f"2. `{rel_path(target_file, COMMON_SKILL)}`",
        f"3. `{rel_path(target_file, COMMON / 'docs' / 'platform-capability-model.md')}`",
        f"4. `{rel_path(target_file, COMMON / 'docs' / 'model-routing.md')}`",
        "",
        "角色约束：",
        "",
        "- `team_lead` 负责分派和结案门槛，不直接执行 live 调试。",
        "- 专家角色的共享 prompt 真相保存在 `../../common/agents/*.md`；`.codex/agents/*.toml` 只负责模型、reasoning、verbosity 与 sandbox。",
        "- remote case 继续服从 `single_runtime_owner`，不得因为 `multi_agent` 就共享 live runtime。",
    ]
    return "\n".join(lines)


def codex_config() -> str:
    lines = [
        'model = "gpt-5.4"',
        'model_reasoning_effort = "high"',
        'model_verbosity = "medium"',
        "",
        "[features]",
        "multi_agent = true",
        "",
        "[windows]",
        'sandbox = "elevated"',
        "",
    ]
    for name, server in MCP_SERVERS["servers"].items():
        lines.extend(
            [
                f"[mcp_servers.{name}]",
                f'command = "{server["command"]}"',
                "args = [" + ", ".join(f'"{arg}"' for arg in server["args"]) + "]",
                "",
            ]
        )
    for role in roles():
        key = role["platform_files"]["codex"]
        lines.extend([f"[agents.{key}]", f'config_file = ".codex/agents/{key}.toml"', ""])
    return "\n".join(lines).rstrip()


def codex_role_config(role: dict, target_file: Path) -> str:
    style = role_style(role["agent_id"])
    prompt_ref = rel_path(target_file, COMMON / role["source_prompt"])
    return f"""# Shared role prompt: {prompt_ref}
model = "{platform_model("codex", role["agent_id"])}"
model_reasoning_effort = "{style["reasoning_effort"]}"
model_verbosity = "{style["verbosity"]}"

[windows]
sandbox = "elevated"
"""


def expected_files(spec: PlatformSpec) -> dict[Path, str]:
    package = package_root(spec.key)
    expected: dict[Path, str] = {}
    expected[package / "README.md"] = normalize(codex_readme() if spec.key == "codex" else readme(spec.key))

    if spec.key in {"claude-code", "code-buddy", "copilot-cli", "copilot-ide"}:
        for role in roles():
            file_name = role["platform_files"].get(spec.key)
            if file_name is None:
                continue
            if spec.key == "claude-code":
                target = package / ".claude" / "agents" / file_name
                expected[target] = normalize(claude_code_agent(role, target))
            elif spec.key == "code-buddy":
                target = package / "agents" / file_name
                expected[target] = normalize(code_buddy_agent(role, target))
            elif spec.key == "copilot-ide":
                target = package / ".github" / "agents" / file_name
                expected[target] = normalize(copilot_ide_agent(role, target))
            elif spec.key == "copilot-cli":
                target = package / "agents" / file_name
                expected[target] = normalize(copilot_cli_agent(role, target))

    if spec.key == "code-buddy":
        target = package / "skills" / "renderdoc-rdc-gpu-debug" / "SKILL.md"
        expected[target] = normalize(skill_wrapper(spec.key, target))
        expected[package / ".codebuddy-plugin" / "plugin.json"] = normalize(json.dumps(code_buddy_plugin(), ensure_ascii=False, indent=2))
        expected[package / ".mcp.json"] = normalize(json.dumps(mcp_payload(), ensure_ascii=False, indent=2))
        expected[package / "hooks" / "hooks.json"] = normalize(json.dumps(code_buddy_hooks(), ensure_ascii=False, indent=2))
    elif spec.key == "copilot-cli":
        target = package / "skills" / "renderdoc-rdc-gpu-debug" / "SKILL.md"
        expected[target] = normalize(skill_wrapper(spec.key, target))
        expected[package / ".copilot-plugin.json"] = normalize(json.dumps(copilot_cli_plugin(), ensure_ascii=False, indent=2))
        expected[package / ".mcp.json"] = normalize(json.dumps(mcp_payload(), ensure_ascii=False, indent=2))
        expected[package / "hooks" / "hooks.json"] = normalize(json.dumps(copilot_cli_hooks(), ensure_ascii=False, indent=2))
    elif spec.key == "claude-code":
        target = package / ".claude" / "CLAUDE.md"
        expected[target] = normalize(claude_code_entry(target))
        expected[package / ".claude" / "settings.json"] = normalize(json.dumps(claude_code_settings(), ensure_ascii=False, indent=2))
    elif spec.key == "copilot-ide":
        skill_target = package / ".github" / "skills" / "renderdoc-rdc-gpu-debug" / "SKILL.md"
        expected[skill_target] = normalize(skill_wrapper(spec.key, skill_target))
        entry_target = package / ".github" / "copilot-instructions.md"
        expected[entry_target] = normalize(copilot_instructions(entry_target))
        ref_target = package / "references" / "entrypoints.md"
        expected[ref_target] = normalize(references_entry(spec.key, ref_target))
        expected[package / "agent-plugin.json"] = normalize(json.dumps(copilot_ide_plugin(), ensure_ascii=False, indent=2))
        expected[package / ".github" / "mcp.json"] = normalize(json.dumps(mcp_payload(), ensure_ascii=False, indent=2))
    elif spec.key == "claude-desktop":
        ref_target = package / "references" / "entrypoints.md"
        expected[ref_target] = normalize(references_entry(spec.key, ref_target))
        expected[package / "claude_desktop_config.json"] = normalize(json.dumps(claude_desktop_config(), ensure_ascii=False, indent=2))
    elif spec.key == "manus":
        ref_target = package / "references" / "entrypoints.md"
        expected[ref_target] = normalize(references_entry(spec.key, ref_target))
        expected[package / "workflows" / "00_debug_workflow.md"] = normalize(manus_workflow())
    elif spec.key == "codex":
        entry = package / "AGENTS.md"
        skill_target = package / ".agents" / "skills" / "renderdoc-rdc-gpu-debug" / "SKILL.md"
        expected[entry] = normalize(codex_agents_md(entry))
        expected[skill_target] = normalize(skill_wrapper(spec.key, skill_target))
        expected[package / ".codex" / "config.toml"] = normalize(codex_config())
        for role in roles():
            key = role["platform_files"]["codex"]
            role_target = package / ".codex" / "agents" / f"{key}.toml"
            expected[role_target] = normalize(codex_role_config(role, role_target))

    return expected


def compare_files(expected: dict[Path, str]) -> list[str]:
    findings: list[str] = []
    for path, content in sorted(expected.items()):
        if not path.exists():
            findings.append(f"missing file: {path}")
            continue
        current = normalize(path.read_text(encoding="utf-8-sig", errors="ignore"))
        if current != content:
            findings.append(f"content drift: {path}")
    return findings


def managed_dir_expectations(spec: PlatformSpec, expected: dict[Path, str]) -> dict[Path, set[str]]:
    package = package_root(spec.key)
    rows: dict[Path, set[str]] = {package / rel_dir: set() for rel_dir in spec.managed_dirs}
    for file_path in expected:
        for directory in rows:
            try:
                rel = file_path.relative_to(directory)
            except ValueError:
                continue
            rows[directory].add(rel.parts[0])
    return rows


def compare_managed_dirs(spec: PlatformSpec, expected: dict[Path, str]) -> list[str]:
    findings: list[str] = []
    for directory, expected_names in managed_dir_expectations(spec, expected).items():
        if not directory.exists():
            if expected_names:
                findings.append(f"missing directory: {directory}")
            continue
        actual_names = {child.name for child in directory.iterdir()}
        for name in sorted(actual_names - expected_names):
            findings.append(f"unexpected scaffold output: {directory / name}")
    return findings


def stale_dirs(spec: PlatformSpec) -> list[str]:
    package = package_root(spec.key)
    findings: list[str] = []
    for rel in FORBIDDEN_DIRS:
        target = package / rel
        if target.exists():
            findings.append(f"forbidden copied shared directory: {target}")
    findings.extend(f"forbidden copy-common artifact: {path}" for path in package.rglob("README.copy-common.md"))
    return findings


def collect_findings(spec: PlatformSpec) -> list[str]:
    expected = expected_files(spec)
    findings: list[str] = []
    findings.extend(compare_files(expected))
    findings.extend(compare_managed_dirs(spec, expected))
    findings.extend(stale_dirs(spec))
    return findings


def remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def sync_spec(spec: PlatformSpec) -> None:
    package = package_root(spec.key)
    for rel in FORBIDDEN_DIRS:
        remove_path(package / rel)
    for rel in spec.managed_dirs:
        remove_path(package / rel)
    for rel in spec.managed_files:
        remove_path(package / rel)
    for path, content in expected_files(spec).items():
        write_text(path, content)


def validate_source_tree() -> list[str]:
    findings: list[str] = []
    for path in (
        COMMON,
        COMMON_AGENTS,
        COMMON_SKILL,
        CONFIG / "role_manifest.json",
        CONFIG / "role_policy.json",
        CONFIG / "model_routing.json",
        CONFIG / "mcp_servers.json",
        CONFIG / "platform_capabilities.json",
        CONFIG / "platform_targets.json",
    ):
        if not path.exists():
            findings.append(f"missing shared source: {path}")
    for role in roles():
        source_prompt = COMMON / role["source_prompt"]
        if not source_prompt.is_file():
            findings.append(f"missing shared agent source: {source_prompt}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync debugger platform scaffolds")
    parser.add_argument("--check", action="store_true", help="Only validate scaffold outputs")
    args = parser.parse_args()

    source_findings = validate_source_tree()
    if source_findings:
        print("[platform scaffold findings]")
        for row in source_findings:
            print(f"  - {row}")
        return 1

    findings = [row for spec in SPECS for row in collect_findings(spec)]
    if args.check:
        if findings:
            print("[platform scaffold findings]")
            for row in findings:
                print(f"  - {row}")
            return 1
        print("platform scaffold check passed")
        return 0

    for spec in SPECS:
        sync_spec(spec)
    print("platform scaffold sync complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
