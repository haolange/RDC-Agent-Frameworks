#!/usr/bin/env python3
"""Validate or refresh the minimal debugger platform scaffold topology."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / "common"
CONFIG_ROOT = COMMON / "config"
FORBIDDEN_DIRS = ("docs", "scripts")
PLATFORMS_WITH_GENERATED_HOOKS = {"code-buddy", "copilot-cli", "cursor"}
LEGACY_ENTRY_SKILL_DIRS = {"renderdoc-rdc-gpu-debug"}


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_text(path: Path, text: str, *, encoding: str = "utf-8-sig") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalize(text), encoding=encoding)


def load_context(root: Path = ROOT) -> dict[str, Any]:
    return {
        "role_manifest": read_json(root / "common" / "config" / "role_manifest.json"),
        "platform_targets": read_json(root / "common" / "config" / "platform_targets.json"),
        "platform_capabilities": read_json(root / "common" / "config" / "platform_capabilities.json"),
        "framework_compliance": read_json(root / "common" / "config" / "framework_compliance.json"),
    }


def platform_target(ctx: dict[str, Any], platform_key: str) -> dict[str, Any]:
    return ctx["platform_targets"]["platforms"][platform_key]


def platform_package_root(ctx: dict[str, Any], platform_key: str) -> Path:
    return ROOT / Path(str(platform_target(ctx, platform_key)["workspace_root"]))


def platform_wrapper_root(ctx: dict[str, Any], platform_key: str) -> Path:
    package = platform_package_root(ctx, platform_key)
    if platform_key == "codex_plugin":
        return package.parent
    return package


def common_placeholder_text() -> str:
    return """# 平台本地 `common/` 占位说明

当前目录是平台本地 `common/` 的最小占位目录，不是正式运行时内容。

使用方式：

1. 选择一个 `debugger/platforms/<platform>/` 模板。
2. 将仓库根目录 `debugger/common/` 整体拷贝到该平台根目录的 `common/`，覆盖当前目录。
3. 完成覆盖后，再在对应宿主中打开该平台根目录使用。

约束：

- 平台内所有 skill、hooks、agents、config 只允许引用当前平台根目录的 `common/`。
- 平台内运行时工作区固定为当前平台根目录下、与 `common/` 和 `tools/` 并列的 `workspace/`。
- 未完成覆盖前，当前平台模板不可用。
- 不为未覆盖状态提供伪完整 placeholder 文件；正式共享正文只来自顶层 `debugger/common/`。
"""


def tools_placeholder_text() -> str:
    return """# 平台本地 `tools/` 占位说明

当前目录是平台本地 `tools/` 的最小占位目录，不是正式运行时内容。

使用方式：

1. 选择一个 `debugger/platforms/<platform>/` 模板。
2. 将 RDC-Agent-Tools 根目录整包拷贝到该平台根目录的 `tools/`，覆盖当前目录。
3. 完成覆盖后，运行 `python common/config/validate_binding.py --strict`，确认 package-local `tools/`、zero-install runtime 与共享绑定均有效。
4. 确认通过后，再在对应宿主中打开该平台根目录使用。

约束：

- 平台内所有 agent / skill / config 引用工具时，只允许引用当前平台根目录的 `tools/` source payload。
- `tools/` 只表示 source payload；live runtime 由 daemon-owned worker 物化到独立 cache 后再加载。
- 未完成覆盖前，当前平台模板不可用。
- 不为未覆盖状态提供伪完整 placeholder 文件；正式工具真相只来自 RDC-Agent-Tools。
"""


def workspace_placeholder_text() -> str:
    return """# 平台本地 `workspace/` 占位说明

当前目录是平台本地 `workspace/` 运行区骨架。

用途：

- 存放通过 `rdc-debugger` intake 之后的 `case_id/run_id` 级运行现场
- 承载 case 级 `inputs/captures/`、run 级 `screenshots/`、`artifacts/`、`logs/`、`notes/`
- 承载第二层交付物 `reports/report.md` 与 `reports/visual_report.html`

约束：

- 这里不是共享真相；共享真相仍由同级 `common/` 提供。
- `workspace/` 是 Agent 运行区，不要求用户手工把 `.rdc` 预放到这里。
- 平台包装层中涉及运行区时，应统一把它表述为当前平台根目录下的 `workspace/`。
- 导入后的原始 `.rdc` 只允许落在 `cases/<case_id>/inputs/captures/`，不得落在 `runs/<run_id>/`
- standalone `capture open` 只建立 tools-layer session state，不会创建这里的 `case/run`
- 这里的 `case/run` 只由已通过的 `rdc-debugger` intake 流程初始化
- 模板仓库只保留占位骨架，不提交真实运行产物。
"""


def cases_placeholder_text() -> str:
    return """# `workspace/cases/` 占位说明

当前目录用于承载运行时 case。

目录约定：

```text
cases/
  <case_id>/
    case.yaml
    inputs/
      captures/
        manifest.yaml
        <capture_id>.rdc
    runs/
      <run_id>/
        run.yaml
        capture_refs.yaml
        artifacts/
        logs/
        notes/
        screenshots/
        reports/
```

规则：

- `.rdc` 是创建 case 的硬前置条件；未提供 capture 时不得初始化 case/run
- `case_id` 是问题实例/需求线程的稳定标识。
- `run_id` 承担 debug version。
- 用户只负责提供 `.rdc`；intake 通过后由 Agent 导入到 `inputs/captures/`。
- 导入后的原始 `.rdc` 只允许落在 `inputs/captures/`；run 只保留 capture 引用与派生产物。
- standalone `capture open` 不会创建这里的 case/run；这里只承载通过 `rdc-debugger` intake 之后的 workspace state。
- 第一层 session artifacts 仍写入同级 `common/knowledge/library/sessions/`；`workspace/` 不复制 gate 真相。
"""


def validate_source_tree(ctx: dict[str, Any]) -> list[str]:
    public_entry_skill = str(
        ((ctx.get("framework_compliance") or {}).get("entry_model") or {}).get("public_entry_skill", "")
    ).strip()
    required = [
        COMMON,
        COMMON / "README.md",
        COMMON / "agents",
        COMMON / "skills" / public_entry_skill / "SKILL.md",
        COMMON / "docs" / "workspace-layout.md",
        COMMON / "knowledge" / "proposals" / "README.md",
        CONFIG_ROOT / "role_manifest.json",
        CONFIG_ROOT / "role_policy.json",
        CONFIG_ROOT / "model_routing.json",
        CONFIG_ROOT / "mcp_servers.json",
        CONFIG_ROOT / "platform_adapter.json",
        CONFIG_ROOT / "platform_capabilities.json",
        CONFIG_ROOT / "platform_targets.json",
        CONFIG_ROOT / "framework_compliance.json",
        CONFIG_ROOT / "tool_catalog.snapshot.json",
    ]
    findings: list[str] = []
    for path in required:
        if not path.exists():
            findings.append(f"missing shared source: {path}")
    for role in ctx["role_manifest"]["roles"]:
        source = COMMON / role["source_prompt"]
        if not source.exists():
            findings.append(f"missing shared agent source: {source}")
        skill = COMMON / role["role_skill_path"]
        if not skill.exists():
            findings.append(f"missing shared role skill: {skill}")
    return findings


def expected_files(ctx: dict[str, Any], platform_key: str) -> set[Path]:
    package = platform_package_root(ctx, platform_key)
    capabilities = ctx["platform_capabilities"]["platforms"][platform_key]
    target = platform_target(ctx, platform_key)
    public_entry_skill = str(
        ((ctx.get("framework_compliance") or {}).get("entry_model") or {}).get("public_entry_skill", "")
    ).strip()
    expected = {
        package / "README.md",
        package / "AGENTS.md",
        package / "common" / "README.md",
        package / "tools" / "README.md",
        package / "workspace" / "README.md",
        package / "workspace" / "cases" / "README.md",
    }

    for rel in capabilities.get("required_paths") or []:
        expected.add(ROOT / rel)

    agent_dir = target.get("agent_dir")
    if agent_dir:
        for role in ctx["role_manifest"]["roles"]:
            file_name = (role.get("platform_files") or {}).get(platform_key)
            if file_name:
                expected.add(package / agent_dir / file_name)

    role_config_dir = target.get("role_config_dir")
    if role_config_dir:
        for role in ctx["role_manifest"]["roles"]:
            file_name = (role.get("platform_files") or {}).get(platform_key)
            if file_name:
                expected.add(package / role_config_dir / f"{file_name}.toml")

    skill_dir = target.get("skill_dir")
    if skill_dir:
        expected.add(package / skill_dir / "SKILL.md")
        skill_root = package / Path(skill_dir).parent
        for role in ctx["role_manifest"]["roles"]:
            expected.add(skill_root / Path(role["role_skill_path"]).parent.name / "SKILL.md")
        expected.add(skill_root / public_entry_skill / "SKILL.md")

    if platform_key in PLATFORMS_WITH_GENERATED_HOOKS:
        expected.add(package / "hooks" / "hooks.json")

    return expected


def compare_placeholder(package: Path, rel_path: str, expected_text: str) -> list[str]:
    path = package / rel_path
    if not path.is_file():
        return [f"missing file: {path}"]
    current = normalize(path.read_text(encoding="utf-8-sig"))
    if current != normalize(expected_text):
        return [f"content drift: {path}"]
    return []


def compare_common_and_workspace(package: Path) -> list[str]:
    findings: list[str] = []
    findings.extend(compare_placeholder(package, "common/README.md", common_placeholder_text()))
    findings.extend(compare_placeholder(package, "tools/README.md", tools_placeholder_text()))
    findings.extend(compare_placeholder(package, "workspace/README.md", workspace_placeholder_text()))
    findings.extend(compare_placeholder(package, "workspace/cases/README.md", cases_placeholder_text()))

    common_dir = package / "common"
    if common_dir.exists():
        children = {child.name for child in common_dir.iterdir()}
        for name in sorted(children - {"README.md"}):
            findings.append(f"unexpected platform-common content: {common_dir / name}")

    tools_dir = package / "tools"
    if tools_dir.exists():
        children = {child.name for child in tools_dir.iterdir()}
        for name in sorted(children - {"README.md"}):
            findings.append(f"unexpected platform-tools content: {tools_dir / name}")

    workspace_dir = package / "workspace"
    if workspace_dir.exists():
        children = {child.name for child in workspace_dir.iterdir()}
        for name in sorted(children - {"README.md", "cases"}):
            findings.append(f"unexpected workspace placeholder content: {workspace_dir / name}")

    cases_dir = workspace_dir / "cases"
    if cases_dir.exists():
        children = {child.name for child in cases_dir.iterdir()}
        for name in sorted(children - {"README.md"}):
            findings.append(f"unexpected cases placeholder content: {cases_dir / name}")

    return findings


def stale_findings(platform_key: str) -> list[str]:
    ctx = load_context(ROOT)
    package = platform_package_root(ctx, platform_key)
    findings: list[str] = []
    for rel in FORBIDDEN_DIRS:
        target = package / rel
        if target.exists():
            findings.append(f"forbidden copied shared directory: {target}")
    for path in package.rglob("README.copy-common.md"):
        findings.append(f"forbidden copy-common artifact: {path}")
    for path in package.rglob("renderdoc-rdc-gpu-debug"):
        findings.append(f"legacy entry skill directory must not exist: {path}")
    return findings


def _public_entry_skill(ctx: dict[str, Any]) -> str:
    return str(((ctx.get("framework_compliance") or {}).get("entry_model") or {}).get("public_entry_skill", "")).strip()


def main_skill_wrapper_text(ctx: dict[str, Any], platform_key: str) -> str:
    platform_row = ctx["platform_capabilities"]["platforms"][platform_key] or {}
    display_name = str(platform_row.get("display_name", platform_key)).strip()
    public_entry_skill = _public_entry_skill(ctx)
    coordination_mode = str(platform_row.get("coordination_mode") or "").strip()
    sub_agent_mode = str(platform_row.get("sub_agent_mode") or "").strip()
    peer_communication = str(platform_row.get("peer_communication") or "").strip()
    agent_description_mode = str(platform_row.get("agent_description_mode") or "").strip()
    specialist_dispatch_requirement = str(platform_row.get("specialist_dispatch_requirement") or "").strip()
    host_delegation_policy = str(platform_row.get("host_delegation_policy") or "").strip()
    host_delegation_fallback = str(platform_row.get("host_delegation_fallback") or "").strip()
    local_live_runtime_policy = str(platform_row.get("local_live_runtime_policy") or "").strip()
    remote_live_runtime_policy = str(platform_row.get("remote_live_runtime_policy") or "").strip()
    policy_notes: list[str] = []
    if local_live_runtime_policy == "multi_context_orchestrated":
        policy_notes.extend([
            "- 当前平台的 local `staged_handoff` 允许 specialist 各持独立 context，但所有协调、brief 重组与裁决都必须经 `rdc-debugger`。",
            "- 跨 context live transfer / resume 只能通过 `runtime_baton`，不得直接跨 specialist 借用 live runtime。",
            "- remote 一律服从 `single_runtime_owner`，不能把 local 的多 context 语义抬到 remote。",
        ])
    elif local_live_runtime_policy == "multi_context_multi_owner":
        policy_notes.extend([
            "- 当前平台的 local `concurrent_team` 允许多个 team agents 各持独立 live context。",
            "- remote 仍统一服从 `single_runtime_owner`。",
        ])
    else:
        policy_notes.append("- 当前平台的 local / remote 都固定按 `single_runtime_owner` 推进 live runtime。")
    if specialist_dispatch_requirement == "required":
        policy_notes.extend([
            "- 默认 `orchestration_mode = multi_agent`；当前平台要求先走 specialist dispatch。",
            "- 只有用户显式要求不要 multi-agent context 时，才允许 `single_agent_by_user`，并且必须把 `single_agent_reason = user_requested` 落盘到 `entry_gate.yaml` 与 `runtime_topology.yaml`。",
            "- specialist dispatch 后，主 agent 必须进入 `waiting_for_specialist_brief` 并持续汇总阶段回报；短时 silence 不得触发 orchestrator 抢活。",
            "- 超过框架预算仍未收到阶段回报时，必须进入 `BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT` 或等价阻断状态，而不是让 orchestrator 抢做 specialist live investigation。",
        ])
    policy_block = "\n".join(policy_notes)
    host_specific_notes = ""
    if platform_key == "codex":
        host_specific_notes = """
- OpenAI Codex 当前原生支持 `AGENTS.md` 分层与 `.codex/agents/*.toml` custom agents；当前模板继续使用这两类原生 surface。
- OpenAI Codex Hooks 当前只对 Bash 提供 guardrail，不足以为本框架的 native `rd.*` / specialist dispatch 提供可靠 host-side enforcement；因此当前模板不引入 `.codex/hooks.json`。
- 当前模板的强制执行链固定为：`.codex/runtime_guard.py preflight` → `entry-gate` → `intake-gate` → `runtime-topology` → `dispatch-readiness` / `specialist-feedback` → `final-audit`。
- 任一 guard 子命令非零退出都必须立即阻断，不得继续 specialist dispatch、live `rd.*` 分析或 finalization。
- direct RenderDoc Python fallback 只允许 local backend；若走直连路径，必须记录 `fallback_execution_mode=local_renderdoc_python` 与 `WRAPPER_DEGRADED_LOCAL_DIRECT`。
- `runtime_guard.py` 只编排 shared validator / gate / audit；平台层不复制 shared schema 或第二套规则正文。
"""
    elif platform_key == "codex_plugin":
        host_specific_notes = """
- 当前插件不依赖 `.codex/config.toml` 或 `.codex/agents/*.toml`。
- specialist 角色以安装型 `skills/` 提供；当需要 specialist 时，`rdc-debugger` 必须显式要求 Codex 创建通用 sub-agent，并让每个 sub-agent 先加载对应的 `skills/<role>/SKILL.md`。
- 当前插件默认入口仍是 `CLI`；只有用户明确要求且已手动启用 `references/mcp-opt-in.sample.toml` 中的配置片段时，才允许切换到 `MCP`。
"""
    return f"""---
name: {public_entry_skill}
description: Public main skill for the RenderDoc/RDC GPU debugger framework. Use when the user wants defect diagnosis, root-cause analysis, regression explanation, or fix verification for a GPU rendering issue from one or more `.rdc` captures.
metadata:
  short-description: RenderDoc/RDC GPU debugging workflow for .rdc captures
---

# `RDC Debugger` 主技能包装说明

当前文件是 {display_name} 的 public main skill 入口。

平台启动后默认保持普通对话态。只有用户手动召唤 `{public_entry_skill}`，才进入 RenderDoc/RDC GPU Debug 调试框架。

进入 `{public_entry_skill}` 后，本 skill 负责：

- `intent_gate`
- `entry_gate`
- preflight
- 缺失输入补料
- intake 规范化
- capture 导入 + case/run 初始化
- `artifacts/intake_gate.yaml`
- `artifacts/runtime_topology.yaml`
- specialist 分派、阶段推进与质量门裁决

固定顺序：

1. `intent_gate`
2. `entry_gate`
3. binding/preflight + capture import + case/run bootstrap
4. `artifacts/intake_gate.yaml` pass
5. `artifacts/runtime_topology.yaml`
6. `{coordination_mode}`
7. `artifacts/run_compliance.yaml` pass

在 `artifacts/intake_gate.yaml` 通过前，不得进入 specialist dispatch 或 live `rd.*` 分析。

本 skill 只引用当前平台根目录的 `common/`：

- common/skills/{public_entry_skill}/SKILL.md
- 进入任何平台真相相关工作前，必须先校验 common/config/platform_adapter.json
- local_support / remote_support / enforcement_layer / coordination_mode 统一以 common/config/platform_capabilities.json 的当前平台定义为准。
- 当前平台的 `sub_agent_mode = {sub_agent_mode}`，`peer_communication = {peer_communication}`，`agent_description_mode = {agent_description_mode}`。
- 当前平台的 `specialist_dispatch_requirement = {specialist_dispatch_requirement}`，`host_delegation_policy = {host_delegation_policy}`，`host_delegation_fallback = {host_delegation_fallback}`。
- local live policy = `{local_live_runtime_policy}`；remote live policy = `{remote_live_runtime_policy}`。
- 当前平台的执行约束补充：
{policy_block}
{host_specific_notes}

未先将顶层 `debugger/common/` 拷入当前平台根目录的 `common/` 之前，不允许在宿主中使用当前平台模板。

运行时 case/run 现场与第二层报告统一写入平台根目录下的 `workspace/`
"""


def role_skill_wrapper_text(ctx: dict[str, Any], platform_key: str, role: dict[str, Any]) -> str:
    platform_row = ctx["platform_capabilities"]["platforms"][platform_key] or {}
    display_name = str(platform_row.get("display_name", platform_key)).strip()
    public_entry_skill = _public_entry_skill(ctx)
    role_skill = str(role["role_skill_path"]).replace("\\", "/")
    role_intro = "该角色默认是 internal/debug-only specialist。平台启动后不会自动进入该角色；只有用户手动召唤 `rdc-debugger` 并由它分派时，才进入当前 role。"
    title = "角色技能包装说明"
    dispatch_note = ""
    role_name = Path(role["role_skill_path"]).parent.name
    role_guidance = ""
    if role_name == "triage-taxonomy":
        role_guidance = (
            "\n\n当前 role 负责读取用户 bug 描述、历史 BugCard/BugFull 与 active taxonomy / invariant / SOP，"
            "\n输出 `candidate_bug_refs`、`recommended_sop` 与 `recommended_investigation_paths` 这类方向建议给 `rdc-debugger`。"
            "\n当前 role 只提供 routing hints，不做根因裁决，不得直接继续 specialist orchestration。"
        )
    elif role_name == "report-knowledge-curator":
        role_guidance = (
            "\n\n当前 role 只在 run 收尾后回看整场调试，判断是否值得新增、更新或 proposal 化 BugCard / BugFull / SOP 等知识对象。"
            "\n当前 role 不参与当前 run 的前置方向建议，也不读取 triage 的知识匹配结果来反向做 specialist dispatch。"
        )
    if platform_key == "codex":
        dispatch_note = (
            "\n\n当前平台的 role gate 由 `rdc-debugger` 通过 `.codex/runtime_guard.py` 统一执行。"
            "\n没有 passed `artifacts/intake_gate.yaml`、passed `artifacts/runtime_topology.yaml` 与主 agent handoff 前，不得进入 live 调查。"
            "\n当前 role 只读消费 gate 结果，不得重判 intent gate，不得直接分派其他 specialist。"
        )
    elif platform_key == "codex_plugin":
        role_name = Path(role["role_skill_path"]).parent.name
        dispatch_note = (
            f"\n\n当前平台不预注册 `.codex/agents` 自定义 agent；如需进入当前 role，`rdc-debugger` "
            f"必须显式要求 Codex 创建通用 sub-agent，并让它先加载当前插件内的 `skills/{role_name}/SKILL.md`。"
        )
    return f"""# {title}

当前文件是 {display_name} 的 role skill 入口。

{role_intro}

先阅读：

1. common/skills/{public_entry_skill}/SKILL.md
2. common/{role_skill}
3. common/config/platform_capabilities.json

当前平台的 `coordination_mode = {str(platform_row.get("coordination_mode") or "").strip()}`，`sub_agent_mode = {str(platform_row.get("sub_agent_mode") or "").strip()}`，`peer_communication = {str(platform_row.get("peer_communication") or "").strip()}`。
{role_guidance}{dispatch_note}

未先将顶层 `debugger/common/` 拷入当前平台根目录的 `common/` 之前，不允许在宿主中使用当前平台模板。
运行时 case/run 现场与第二层报告统一写入平台根目录下的 `workspace/`
"""


def codex_plugin_manifest_text() -> str:
    manifest = {
        "name": "rdc-debugger",
        "version": "0.1.0",
        "description": "RenderDoc/RDC GPU Debug 的 Codex plugin 包装层，要求先手动覆盖 common/ 与 tools/ 后再使用。",
        "author": {
            "name": "[TODO: maintainer-name]",
            "email": "[TODO: maintainer-email]",
            "url": "[TODO: maintainer-url]",
        },
        "homepage": "[TODO: homepage-url]",
        "repository": "[TODO: repository-url]",
        "license": "[TODO: SPDX-license-id]",
        "keywords": [
            "renderdoc",
            "rdc",
            "gpu",
            "debug",
            "codex",
            "plugin",
        ],
        "skills": "./skills/",
        "interface": {
            "displayName": "RDC Debugger",
            "shortDescription": "RenderDoc/RDC GPU debugging workflow",
            "longDescription": "CLI-first Codex plugin bundle for RenderDoc/RDC GPU debugging. You still need to copy debugger/common and RDC-Agent-Tools into the plugin before validating and installing it.",
            "developerName": "RenderDoc/RDC GPU Debug",
            "category": "Developer Tools",
            "capabilities": [
                "Read",
                "Write",
            ],
            "websiteURL": "[TODO: website-url]",
            "privacyPolicyURL": "[TODO: privacy-policy-url]",
            "termsOfServiceURL": "[TODO: terms-of-service-url]",
            "defaultPrompt": [
                "Use $rdc-debugger to enter the RenderDoc/RDC GPU debugging workflow for this workspace.",
                "Use $rdc-debugger to diagnose this .rdc capture.",
                "Use $rdc-debugger to verify whether this render fix is correct."
            ],
            "brandColor": "#0F766E",
        },
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2)


def codex_plugin_skill_openai_yaml_text() -> str:
    return """interface:
  display_name: "RDC Debugger"
  short_description: "Enter the RenderDoc/RDC GPU debugging workflow for .rdc captures"
  default_prompt: "Use $rdc-debugger to enter the RenderDoc/RDC GPU debugging workflow for this workspace."

policy:
  allow_implicit_invocation: true
"""


def codex_plugin_outer_readme_text() -> str:
    return """# Codex Plugin Wrapper（外层包装目录）

当前目录是 Codex plugin 的外层包装目录，不是可直接安装或运行的 plugin root。

真正符合 Codex plugin 规范的根目录位于同级 `rdc-debugger/`。

## 目录职责

- `rdc-debugger/`：唯一可安装的 Codex plugin bundle。
- `references/personal-marketplace.sample.json`：个人 marketplace 示例，目标位置是 `~/.agents/plugins/marketplace.json`。
- 当前外层目录只负责包装说明、安装链路与 marketplace 示例；运行时规则仍以 `rdc-debugger/` 与共享 `debugger/common/` 为准。

## 安装链路

1. 将仓库根目录 `debugger/common/` 整体拷贝到 `rdc-debugger/common/`。
2. 将 `RDC-Agent-Tools` 根目录整包拷贝到 `rdc-debugger/tools/`。
3. 在 `rdc-debugger/` 根目录运行 `python common/config/validate_binding.py --strict`，确认 package-local `tools/`、zero-install runtime 与共享绑定全部通过。
4. 将 `rdc-debugger/` 同步到 `~/.agents/plugins/rdc-debugger/`。
5. 将 `references/personal-marketplace.sample.json` 合并到 `~/.agents/plugins/marketplace.json`。
6. 在 Codex 中打开 `/plugins`，安装或刷新 `rdc-debugger`。
7. 安装后在新线程中使用 `@RDC Debugger` 或 `$rdc-debugger` 进入框架。

## 约束

- 不要把当前外层目录当作 plugin root。
- `common/` 与 `tools/` 仍然是用户手动覆盖的 package-local payload，不会随插件自动内置。
- Codex 本地插件安装后实际加载的是 cache 副本；每次重新覆盖 `common/` 或 `tools/` 后，都必须重新同步 `~/.agents/plugins/rdc-debugger/`，然后在 `/plugins` 中刷新或重装。
"""


def codex_plugin_outer_agents_text() -> str:
    return """# Codex Plugin Wrapper Instructions（外层包装约束）

当前目录只负责 Codex plugin 的包装说明，不是运行时 plugin root。

规则：

- 唯一可安装插件根目录固定为同级 `rdc-debugger/`。
- 运行时约束、skills、workspace 语义、`common/` / `tools/` 占位都只在 `rdc-debugger/` 与共享 `debugger/common/` 中维护。
- 当前外层目录只允许放包装说明、安装说明与 marketplace 示例，不要在这里复制 framework 运行规则。
- `references/personal-marketplace.sample.json` 必须继续指向 `./plugins/rdc-debugger`，不要改成旧路径或 source repo 路径。
"""


def codex_plugin_inner_readme_text() -> str:
    return """# Codex Plugin Bundle（插件包）

当前目录是 Codex 的 installable plugin bundle。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

入口规则：

- 当前宿主可直接访问本地进程、文件系统与 workspace，默认采用 local-first。
- 默认入口是 daemon-backed `CLI`；只有用户明确要求按 `MCP` 接入且已手动启用 `references/mcp-opt-in.sample.toml` 中的配置片段时，才切换到 `MCP`。
- 任务开始时，Agent 必须向用户说明当前采用的是 `CLI` 还是 `MCP`。
- 若用户要求 `MCP`，但宿主尚未按 sample 配置对应 server，必须直接阻断并提示配置。
- 当前插件不会在 manifest 中默认预注册 MCP；`MCP` 只通过文档化 opt-in 提供。
- 当前平台的 `local_support` / `remote_support` / `enforcement_layer` 以 `common/config/platform_capabilities.json` 中 `codex_plugin` 行为准。

使用方式：

1. 将仓库根目录 `debugger/common/` 整体拷贝到当前插件根目录的 `common/`，覆盖占位内容。
2. 将 `RDC-Agent-Tools` 根目录整包拷贝到当前插件根目录的 `tools/`，覆盖占位内容。
3. 确认 `tools/` 下存在 `validation.required_paths` 列出的必需文件。
4. 运行 `python common/config/validate_binding.py --strict`，确认 package-local `tools/`、zero-install runtime、snapshot、共享文档与插件包根目录全部对齐。
5. 使用当前插件根目录下、与 `common/` 和 `tools/` 并列的 `workspace/` 作为运行区。
6. 将当前目录同步到 `~/.agents/plugins/rdc-debugger/`。
7. 将 `../references/personal-marketplace.sample.json` 合并到 `~/.agents/plugins/marketplace.json`。
8. 在 Codex 中打开 `/plugins` 安装或刷新 `rdc-debugger`。
9. 平台启动后默认保持普通对话态；只有用户手动召唤 `rdc-debugger`，才进入调试框架。除 `rdc-debugger` 之外，其他 specialist 默认都是 internal/debug-only。

约束：

- `common/` 默认只保留一个占位文件；正式共享正文仍由顶层 `debugger/common/` 提供，并由用户显式拷入。
- 未完成 `debugger/common/` 覆盖、`tools/` 覆盖或 binding 校验前，Agent 必须拒绝执行依赖平台真相的工作。
- 未提供可导入的 `.rdc` 时，Agent 必须以 `BLOCKED_MISSING_CAPTURE` 直接阻断，不得初始化 case/run 或继续 triage、investigation、planning。
- 当前插件不依赖 `.codex/config.toml` 或 `.codex/agents/*.toml`；specialist 角色通过安装型 `skills/` 提供，并由 `rdc-debugger` 显式要求 Codex 创建通用 sub-agent 后加载。
- 当前工具 snapshot 必须与 `RDC-Agent-Tools` 当前 catalog 完整对齐，并覆盖 `rd.vfs.*` 导航层、扩展 `rd.session.*`、`rd.core.*` discovery/observability，以及 bounded event-tree 读取语义；其中 `tabular/tsv` 仅作为 projection 支持。
- 本地 plugin 安装后实际运行的是 Codex cache 副本，而不是 source repo 当前目录；每次重新覆盖 `common/` 或 `tools/` 后，都必须重新同步 `~/.agents/plugins/rdc-debugger/`，再在 `/plugins` 中刷新或重装。
"""


def codex_plugin_inner_agents_text() -> str:
    return """# Codex Plugin Workspace Instructions（工作区约束）

当前目录是 Codex 的 installable plugin bundle。所有角色在进入 role-specific 行为前，都必须先服从本文件与共享 `common/` 约束。

## 前置检查（必须先于任何其他步骤执行）

在执行任何工作前，必须验证以下两项均已就绪：

1. `common/` 已正确覆盖：检查 `common/AGENT_CORE.md` 是否存在。
2. `tools/` 已正确覆盖：检查 `tools/spec/tool_catalog.json` 与 `tools/rdx.bat` 是否存在。

任一文件不存在时：

- 立即停止，不得继续任何工作。
- 不得降级处理、搜索替代工具路径、使用模型记忆或以其他方式绕过本检查。
- 向用户输出：

```
前置环境未就绪：请确认 (1) 已将 debugger/common/ 整包覆盖到平台根 common/；(2) 已将 RDC-Agent-Tools 整包覆盖到平台根 tools/；(3) 在平台根目录运行 python common/config/validate_binding.py --strict 通过后，再重新发起任务。
```

验证通过后，按顺序阅读：

1. common/AGENT_CORE.md
2. common/config/platform_adapter.json
3. skills/rdc-debugger/SKILL.md
4. common/docs/platform-capability-model.md
5. common/docs/model-routing.md

强制规则：

- 平台启动后默认保持普通对话态；只有用户手动召唤 `rdc-debugger`，才进入 RenderDoc/RDC GPU Debug 调试框架。
- 除 `rdc-debugger` 之外，其他 specialist 默认都是 internal/debug-only，只能由 `rdc-debugger` 在框架内分派。
- 用户尚未提供可导入的 `.rdc` 时，必须以 `BLOCKED_MISSING_CAPTURE` 停止，不得初始化 case/run 或继续做 debug、investigation、tool planning。
- 当前插件不预注册 `.codex/agents` 自定义 agent；如需 specialist 角色，`rdc-debugger` 必须显式要求 Codex 创建通用 sub-agent，并让它先加载当前插件内的对应 `skills/<role>/SKILL.md`。
- `codex_plugin` 的 `local_support` / `remote_support` / `enforcement_layer` 以 `common/config/platform_capabilities.json` 当前行与 `runtime_mode_truth.snapshot.json` 为准。

未先将 `debugger/common/` 整包覆盖到平台根 `common/`、且将 RDC-Agent-Tools 整包覆盖到平台根 `tools/` 之前，不允许在宿主中使用当前插件包。

运行时工作区固定为平台根目录下的 `workspace/`

- 当前插件路径按 `no-hooks` 处理；Codex 的执行门禁固定为：
  1. `intent_gate`
  2. `accept-intake`（内部顺序执行 `entry_gate -> capture import -> case/run bootstrap -> intake_gate -> runtime_topology`）
  3. `dispatch_readiness` / `dispatch_specialist` / `specialist_feedback`
  4. `staged_handoff`
  5. `artifacts/run_compliance.yaml` pass
- 在 `artifacts/intake_gate.yaml` 通过前，不得执行 specialist dispatch 或 live `rd.*` 调试。
"""


def codex_plugin_marketplace_sample_text() -> str:
    marketplace = {
        "name": "local-personal",
        "interface": {
            "displayName": "Local Personal Plugins",
        },
        "plugins": [
            {
                "name": "rdc-debugger",
                "source": {
                    "source": "local",
                    "path": "./plugins/rdc-debugger",
                },
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": "Developer Tools",
            }
        ],
    }
    return json.dumps(marketplace, ensure_ascii=False, indent=2)


def codex_plugin_mcp_opt_in_text() -> str:
    return """# Copy this snippet into ~/.codex/config.toml only when you explicitly want to use MCP.
# Set RDC_DEBUGGER_PLUGIN_ROOT to ~/.agents/plugins/rdc-debugger before using this sample,
# or replace the variable with the literal absolute path of that directory.

[mcp_servers.renderdoc-platform-mcp]
command = "cmd"
args = ["/c", "${RDC_DEBUGGER_PLUGIN_ROOT}/tools/rdx.bat", "--non-interactive", "mcp"]
"""


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", text
    return f"---{parts[1]}---\n\n", parts[2].lstrip("\r\n")


def _path_prefix_to_package_root(relative_dir: str) -> str:
    parts = [part for part in Path(relative_dir).parts if part not in {"", "."}]
    return "../" * len(parts)


def _agent_wrapper_encoding(platform_key: str) -> str:
    return "utf-8" if platform_key == "claude-code" else "utf-8-sig"


def agent_wrapper_body_text(ctx: dict[str, Any], platform_key: str, role: dict[str, Any]) -> str:
    display_name = str((ctx["platform_capabilities"]["platforms"][platform_key] or {}).get("display_name", platform_key)).strip()
    target = ctx["platform_targets"]["platforms"][platform_key]
    public_entry_skill = _public_entry_skill(ctx)
    source_prompt = str(role["source_prompt"]).replace("\\", "/")
    role_skill = str(role["role_skill_path"]).replace("\\", "/")
    package_prefix = _path_prefix_to_package_root(str(target.get("agent_dir") or ""))

    if platform_key == "cursor":
        host_name = "Cursor IDE"
    else:
        host_name = display_name

    role_intro = "该角色默认是 internal/debug-only specialist。平台启动后不会自动进入该角色；只有用户手动召唤 `rdc-debugger` 并由它完成分派时，才进入当前 role。"
    extra = ""
    role_name = Path(role["role_skill_path"]).parent.name
    if role_name == "triage-taxonomy":
        extra = (
            "当前 role 负责读取用户 bug 描述、BugCard/BugFull 历史案例与 active taxonomy / invariant / SOP，"
            "输出 `candidate_bug_refs`、`recommended_sop` 与 `recommended_investigation_paths` 给主 agent；"
            "它只提供 routing hints，不做根因裁决，也不继续 orchestration。"
        )
    elif role_name == "report-knowledge-curator":
        extra = (
            "当前 role 只在 run 收尾后回看整场调试，判断是否值得新增、更新或 proposal 化知识对象；"
            "它不参与当前 run 的前置方向建议，也不反向做 specialist dispatch。"
        )

    tail = ("\n\n" + extra) if extra else ""
    return f"""# RenderDoc/RDC Agent 宿主入口

当前文件是 {host_name} 宿主入口。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

本文件只负责宿主入口与角色元数据；共享正文统一从当前平台根目录的 `common/` 读取。

{role_intro}

按顺序阅读：

1. {package_prefix}AGENTS.md
2. {package_prefix}common/AGENT_CORE.md
3. {package_prefix}common/{source_prompt}
4. {package_prefix}common/skills/{public_entry_skill}/SKILL.md
5. {package_prefix}common/{role_skill}

未先将顶层 `debugger/common/` 拷入当前平台根目录的 `common/` 之前，不允许在宿主中使用当前平台模板。{tail}

运行时工作区固定为平台根目录下的 `workspace/`
"""


def collect_findings(ctx: dict[str, Any], platform_key: str) -> list[str]:
    package = platform_package_root(ctx, platform_key)
    findings: list[str] = []
    for path in sorted(expected_files(ctx, platform_key)):
        if not path.exists():
            findings.append(f"missing file: {path}")
    findings.extend(compare_common_and_workspace(package))
    findings.extend(stale_findings(platform_key))
    return findings


def sync_placeholders(ctx: dict[str, Any], platform_key: str) -> None:
    package = platform_package_root(ctx, platform_key)
    for rel in FORBIDDEN_DIRS:
        target = package / rel
        if target.exists():
            shutil.rmtree(target)
    write_text(package / "common" / "README.md", common_placeholder_text())
    write_text(package / "tools" / "README.md", tools_placeholder_text())
    write_text(package / "workspace" / "README.md", workspace_placeholder_text())
    write_text(package / "workspace" / "cases" / "README.md", cases_placeholder_text())


def sync_skill_wrappers(ctx: dict[str, Any], platform_key: str) -> None:
    package = platform_package_root(ctx, platform_key)
    target = platform_target(ctx, platform_key)
    skill_dir = target.get("skill_dir")
    if not skill_dir:
        return

    skill_root = package / Path(skill_dir).parent
    public_entry_skill = _public_entry_skill(ctx)
    desired_names = {public_entry_skill}

    write_text(skill_root / public_entry_skill / "SKILL.md", main_skill_wrapper_text(ctx, platform_key))
    for role in ctx["role_manifest"]["roles"]:
        role_name = Path(role["role_skill_path"]).parent.name
        desired_names.add(role_name)
        write_text(skill_root / role_name / "SKILL.md", role_skill_wrapper_text(ctx, platform_key, role))

    if skill_root.is_dir():
        for child in skill_root.iterdir():
            if not child.is_dir():
                continue
            if child.name in LEGACY_ENTRY_SKILL_DIRS or child.name not in desired_names:
                shutil.rmtree(child)


def sync_agent_and_role_configs(ctx: dict[str, Any], platform_key: str) -> None:
    package = platform_package_root(ctx, platform_key)
    target = platform_target(ctx, platform_key)
    desired_files = {
        str((role.get("platform_files") or {}).get(platform_key, "")).strip()
        for role in ctx["role_manifest"]["roles"]
        if str((role.get("platform_files") or {}).get(platform_key, "")).strip()
    }

    agent_dir = str(target.get("agent_dir") or "").strip()
    if agent_dir:
        agent_root = package / agent_dir
        if agent_root.is_dir():
            for child in agent_root.iterdir():
                if child.is_file() and child.name not in desired_files:
                    child.unlink()

    role_config_dir = str(target.get("role_config_dir") or "").strip()
    if role_config_dir:
        role_root = package / role_config_dir
        if role_root.is_dir():
            desired_config_names = {f"{name}.toml" for name in desired_files}
            if platform_key == "codex":
                desired_config_names.add("rdc-debugger.toml")
            for child in role_root.iterdir():
                if child.is_file() and child.name not in desired_config_names:
                    child.unlink()


def sync_agent_wrappers(ctx: dict[str, Any], platform_key: str) -> None:
    package = platform_package_root(ctx, platform_key)
    target = platform_target(ctx, platform_key)
    agent_dir = str(target.get("agent_dir") or "").strip()
    if not agent_dir:
        return

    for role in ctx["role_manifest"]["roles"]:
        file_name = (role.get("platform_files") or {}).get(platform_key)
        if not file_name:
            continue
        path = package / agent_dir / file_name
        if not path.is_file():
            continue
        frontmatter, _ = _split_frontmatter(path.read_text(encoding="utf-8-sig"))
        write_text(
            path,
            frontmatter + agent_wrapper_body_text(ctx, platform_key, role),
            encoding=_agent_wrapper_encoding(platform_key),
        )


def sync_platform_specific_files(ctx: dict[str, Any], platform_key: str) -> None:
    if platform_key != "codex_plugin":
        return

    package = platform_package_root(ctx, platform_key)
    wrapper_root = platform_wrapper_root(ctx, platform_key)
    public_entry_skill = _public_entry_skill(ctx)

    write_text(wrapper_root / "README.md", codex_plugin_outer_readme_text())
    write_text(wrapper_root / "AGENTS.md", codex_plugin_outer_agents_text())
    write_text(
        wrapper_root / "references" / "personal-marketplace.sample.json",
        codex_plugin_marketplace_sample_text(),
        encoding="utf-8",
    )
    write_text(package / "README.md", codex_plugin_inner_readme_text())
    write_text(package / "AGENTS.md", codex_plugin_inner_agents_text())
    write_text(
        package / ".codex-plugin" / "plugin.json",
        codex_plugin_manifest_text(),
        encoding="utf-8",
    )
    write_text(
        package / "references" / "mcp-opt-in.sample.toml",
        codex_plugin_mcp_opt_in_text(),
        encoding="utf-8",
    )
    write_text(
        package / "skills" / public_entry_skill / "agents" / "openai.yaml",
        codex_plugin_skill_openai_yaml_text(),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or refresh minimal debugger platform scaffolds")
    parser.add_argument("--check", action="store_true", help="Validate scaffold topology without rewriting placeholders")
    args = parser.parse_args(argv)

    ctx = load_context(ROOT)

    if args.check:
        findings = validate_source_tree(ctx)
        for platform_key in ctx["platform_capabilities"]["platforms"]:
            findings.extend(collect_findings(ctx, platform_key))
        if findings:
            print("[platform scaffold findings]")
            for row in findings:
                print(f" - {row}")
            return 1
        print("platform scaffold check passed")
        return 0

    for platform_key in ctx["platform_capabilities"]["platforms"]:
        sync_placeholders(ctx, platform_key)
        sync_skill_wrappers(ctx, platform_key)
        sync_platform_specific_files(ctx, platform_key)
        sync_agent_and_role_configs(ctx, platform_key)
        sync_agent_wrappers(ctx, platform_key)
    findings = validate_source_tree(ctx)
    for platform_key in ctx["platform_capabilities"]["platforms"]:
        findings.extend(collect_findings(ctx, platform_key))
    if findings:
        print("[platform scaffold findings]")
        for row in findings:
            print(f" - {row}")
        return 1
    print("platform scaffold sync complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
