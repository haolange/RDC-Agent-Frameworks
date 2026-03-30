#!/usr/bin/env python3
"""Repository-level debugger validator."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_yaml(path: Path):
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise RuntimeError("PyYAML is required to read debugger YAML specs") from exc
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def _print_proc(proc: subprocess.CompletedProcess[str]) -> None:
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)


def _surface_supported(platform_caps: dict, surface: str) -> bool:
    if surface == "workflow":
        return bool(platform_caps.get("coordination_mode") == "workflow_stage" or platform_caps.get("degradation_mode") == "workflow-package")
    if surface == "agents":
        surface = "custom_agents"
    caps = platform_caps.get("capabilities") or {}
    slot = caps.get(surface) or {}
    return bool(slot.get("supported"))


def _frontmatter_string(path: Path, field: str) -> str | None:
    text = path.read_text(encoding="utf-8-sig")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    match = re.search(rf"^{re.escape(field)}:\s*\"?([^\r\n\"]+)\"?\s*$", parts[1], re.MULTILINE)
    return match.group(1).strip() if match else None


def _toml_string(path: Path, key: str) -> str | None:
    text = path.read_text(encoding="utf-8-sig")
    match = re.search(rf"^{re.escape(key)}\s*=\s*\"([^\r\n\"]+)\"\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def _platform_renders_per_agent_model(platform_caps: dict) -> bool:
    slot = (platform_caps.get("capabilities") or {}).get("per_agent_model") or {}
    rendered = str(slot.get("rendered", "")).strip()
    return bool(slot.get("supported")) and rendered not in {"inherit", "workflow-level", "not-supported"}


def _platform_is_inherit_only(platform_caps: dict) -> bool:
    slot = (platform_caps.get("capabilities") or {}).get("per_agent_model") or {}
    rendered = str(slot.get("rendered", "")).strip()
    return (not bool(slot.get("supported"))) or rendered in {"inherit", "workflow-level", "not-supported"}


def _claude_code_subagent_name(role: dict) -> str | None:
    platform_names = role.get("platform_subagent_names") or {}
    value = str(platform_names.get("claude-code", "")).strip()
    return value or None


def _agent_allowlist(value: str | None) -> set[str]:
    if not value:
        return set()
    match = re.search(r"Agent\(([^)]*)\)", value)
    if not match:
        return set()
    return {item.strip() for item in match.group(1).split(",") if item.strip()}


def _expected_rendered_model(root: Path, platform_key: str, agent_id: str) -> tuple[Path, str] | None:
    manifest = _read_json(root / "common" / "config" / "role_manifest.json")
    routing = _read_json(root / "common" / "config" / "model_routing.json")
    role_profiles = routing.get("role_profiles") or {}
    profiles = routing.get("profiles") or {}
    roles = {row["agent_id"]: row for row in manifest.get("roles") or []}
    role = roles.get(agent_id)
    if not role:
        return None
    platform_file = (role.get("platform_files") or {}).get(platform_key)
    if not platform_file:
        return None
    profile_name = role_profiles.get(agent_id)
    profile = profiles.get(profile_name) or {}
    expected_model = ((profile.get("platform_rendering") or {}).get(platform_key) or "").strip()
    if platform_key == "code-buddy":
        path = root / "platforms" / platform_key / "agents" / platform_file
    elif platform_key == "claude-code":
        path = root / "platforms" / platform_key / ".claude" / "agents" / platform_file
    elif platform_key == "copilot-cli":
        path = root / "platforms" / platform_key / "agents" / platform_file
    elif platform_key == "copilot-ide":
        path = root / "platforms" / platform_key / ".github" / "agents" / platform_file
    elif platform_key == "cursor":
        path = root / "platforms" / platform_key / "agents" / platform_file
    elif platform_key == "codex":
        path = root / "platforms" / platform_key / ".codex" / "agents" / f"{platform_file}.toml"
    else:
        return None
    return path, expected_model


def _role_manifest_findings(root: Path) -> list[str]:
    findings: list[str] = []
    manifest = _read_json(root / "common" / "config" / "role_manifest.json")
    caps = _read_json(root / "common" / "config" / "platform_capabilities.json")
    platform_rows = caps.get("platforms") or {}

    required_platforms = {
        platform_key
        for platform_key, platform_caps in platform_rows.items()
        if bool(((platform_caps.get("capabilities") or {}).get("custom_agents") or {}).get("supported"))
    }

    for role in manifest.get("roles") or []:
        platform_files = set((role.get("platform_files") or {}).keys())
        if platform_files != required_platforms:
            findings.append(
                f"{role.get('agent_id')}: platform_files keys differ from custom_agents-supported platforms"
            )

    return findings


def _platform_wrapper_path_findings(root: Path) -> list[str]:
    findings: list[str] = []
    platform_root = root / "platforms"
    text_exts = {".md", ".txt", ".json", ".toml", ".yaml", ".yml"}
    relative_ref_pattern = re.compile(r"(?P<ref>(?:\.\./)+[A-Za-z0-9_.-][A-Za-z0-9_./-]*)")

    for path in platform_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_exts:
            continue
        text = path.read_text(encoding="utf-8-sig")
        try:
            platform_dir = path.relative_to(platform_root).parts[0]
        except ValueError:
            continue
        package_root = (platform_root / platform_dir).resolve()
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("@"):
                continue
            for match in relative_ref_pattern.finditer(line):
                marker = match.group("ref")
                resolved = (path.parent / marker).resolve()
                try:
                    resolved.relative_to(package_root)
                except ValueError:
                    findings.append(
                        f"{path}:{lineno}: platform wrapper relative path escapes platform root '{marker}'"
                    )

    cursor_rules = (platform_root / "cursor" / ".cursor" / "rules" / "rdc-debugger.mdc").read_text(encoding="utf-8-sig")
    if "正常用户请求只能从 `rdc-debugger` 进入" in cursor_rules:
        findings.append("cursor/.cursor/rules/rdc-debugger.mdc must not declare rdc-debugger as the normal user entry")
    if "rdc-debugger" not in cursor_rules:
        findings.append("cursor/.cursor/rules/rdc-debugger.mdc must declare rdc-debugger as the normal user entry")

    return findings


def _doc_contract_findings(root: Path) -> list[str]:
    findings: list[str] = []
    matrix = (root / "common" / "docs" / "platform-capability-matrix.md").read_text(encoding="utf-8-sig")
    model_doc = (root / "common" / "docs" / "platform-capability-model.md").read_text(encoding="utf-8-sig")
    runtime_doc = (root / "common" / "docs" / "runtime-coordination-model.md").read_text(encoding="utf-8-sig")
    workspace_doc = (root / "common" / "docs" / "workspace-layout.md").read_text(encoding="utf-8-sig")
    core_doc = (root / "common" / "AGENT_CORE.md").read_text(encoding="utf-8-sig")
    intake_doc = (root / "common" / "docs" / "intake" / "README.md").read_text(encoding="utf-8-sig")
    main_skill = (root / "common" / "skills" / "rdc-debugger" / "SKILL.md").read_text(encoding="utf-8-sig")
    triage_agent_doc = (root / "common" / "agents" / "02_triage_taxonomy.md").read_text(encoding="utf-8-sig")
    triage_skill = (root / "common" / "skills" / "triage-taxonomy" / "SKILL.md").read_text(encoding="utf-8-sig")
    curator_agent_doc = (root / "common" / "agents" / "09_report_knowledge_curator.md").read_text(encoding="utf-8-sig")
    curator_skill = (root / "common" / "skills" / "report-knowledge-curator" / "SKILL.md").read_text(encoding="utf-8-sig")
    claude_code_readme = (root / "platforms" / "claude-code" / "README.md").read_text(encoding="utf-8-sig")
    codex_readme = (root / "platforms" / "codex" / "README.md").read_text(encoding="utf-8-sig")
    codex_agents = (root / "platforms" / "codex" / "AGENTS.md").read_text(encoding="utf-8-sig")
    manus_readme = (root / "platforms" / "manus" / "README.md").read_text(encoding="utf-8-sig")
    manus_entrypoints = (root / "platforms" / "manus" / "references" / "entrypoints.md").read_text(encoding="utf-8-sig")
    manus_workflow = (root / "platforms" / "manus" / "workflows" / "00_debug_workflow.md").read_text(encoding="utf-8-sig")

    required_matrix_rows = [
        "| Code Buddy |",
        "| Claude Code |",
        "| Copilot CLI |",
        "| Copilot IDE |",
        "| Claude Desktop |",
        "| Manus |",
        "| Codex |",
        "| Cursor |",
    ]
    for row in required_matrix_rows:
        if row not in matrix:
            findings.append(f"platform-capability-matrix.md missing platform row: {row}")

    if "文档镜像，不是独立 SSOT" not in matrix:
        findings.append("platform-capability-matrix.md must state it is not an independent SSOT")
    if "Default Entry" not in matrix or "Allowed Entry Modes" not in matrix:
        findings.append("platform-capability-matrix.md must expose entry mode columns")
    if "Sub-Agent Mode" not in matrix or "Peer Communication" not in matrix or "Dispatch Topology" not in matrix:
        findings.append("platform-capability-matrix.md must expose agentic capability columns")
    if "multi_context_orchestrated" not in matrix:
        findings.append("platform-capability-matrix.md must expose multi_context_orchestrated local policy")
    if "| Claude Code |" in matrix and "CLI, MCP" not in matrix:
        findings.append("platform-capability-matrix.md must show CLI, MCP entry coverage")
    if "| Manus |" in matrix and "MCP only" not in matrix:
        findings.append("platform-capability-matrix.md must mark Manus as MCP only")
    if "唯一权威源" not in model_doc:
        findings.append("platform-capability-model.md must state JSON SSOT ownership")
    if "sub agent 支持不等于 team agents" not in model_doc:
        findings.append("platform-capability-model.md must distinguish sub agents from team agents")
    if "staged_handoff" not in model_doc or "hub-and-spoke" not in model_doc:
        findings.append("platform-capability-model.md must define staged_handoff as hub-and-spoke handoff")
    if "multi_context_orchestrated" not in model_doc:
        findings.append("platform-capability-model.md must document multi_context_orchestrated for staged_handoff local")
    if "serial_only" not in model_doc or "single_runtime_owner" not in model_doc:
        findings.append("platform-capability-model.md must describe formal remote support levels and single_runtime_owner")
    if "并行 case 也必须拆成独立 `context/daemon`" not in runtime_doc:
        findings.append("runtime-coordination-model.md must define parallel case isolation")
    if "remote_coordination_mode = single_runtime_owner" not in runtime_doc:
        findings.append("runtime-coordination-model.md must define single_runtime_owner remote coordination")
    if "single_runtime_owner != single_agent_flow" not in runtime_doc:
        findings.append("runtime-coordination-model.md must state that single_runtime_owner is not single_agent_flow")
    if "staged_handoff" not in runtime_doc or "多 specialist 多轮接力" not in runtime_doc:
        findings.append("runtime-coordination-model.md must define staged_handoff as multi-round specialist handoff")
    if "delegation_status" not in runtime_doc or "orchestration_mode" not in runtime_doc:
        findings.append("runtime-coordination-model.md must document orchestration_mode and delegation_status artifacts")
    if "single_agent_by_user" not in runtime_doc or "BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT" not in runtime_doc:
        findings.append("runtime-coordination-model.md must document single_agent_by_user and specialist feedback timeout semantics")
    if "并行 case 只能共享仓库，不得共享同一条 live `context`" not in workspace_doc:
        findings.append("workspace-layout.md must define case/context isolation")
    if "`rdc-debugger` 是唯一 framework classifier" not in core_doc:
        findings.append("AGENT_CORE.md must declare rdc-debugger as the only framework classifier")
    if "不得重做 framework 判定" not in core_doc:
        findings.append("AGENT_CORE.md must forbid downstream framework reclassification")
    if "misroute 必须 reject + redirect" not in intake_doc:
        findings.append("intake/README.md must require reject + redirect for misroutes")
    if "多轮期间不创建 case/run" not in intake_doc:
        findings.append("intake/README.md must state that clarification rounds do not create case/run")
    if "A/B 本身不等于 analyst" not in main_skill:
        findings.append("rdc-debugger skill must state that A/B alone does not imply analyst")
    if "primary_completion_question" not in main_skill or "dominant_operation" not in main_skill or "requested_artifact" not in main_skill or "ab_role" not in main_skill:
        findings.append("rdc-debugger skill must define the intent_gate first-principles dimensions")
    if "拒绝进入 `debugger`" not in main_skill:
        findings.append("rdc-debugger skill must define reject-and-redirect behavior")
    if "多轮澄清" not in main_skill:
        findings.append("rdc-debugger skill must allow multi-round clarification before classification stabilizes")
    if "在当前对话上传" not in core_doc or "文件路径" not in core_doc:
        findings.append("AGENT_CORE.md must allow uploaded captures and accessible file paths")
    if "single_agent_by_user" not in core_doc or "BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT" not in core_doc:
        findings.append("AGENT_CORE.md must define explicit single-agent mode and specialist feedback timeout handling")
    if "历史 BugCard / BugFull" not in core_doc or "探索方向建议" not in core_doc:
        findings.append("AGENT_CORE.md must define triage historical-case matching as routing hints for the main agent")
    if "knowledge/library/bugcards/" not in triage_agent_doc or "knowledge/library/bugfull/" not in triage_agent_doc:
        findings.append("triage agent doc must load BugCard/BugFull history as triage inputs")
    if "candidate_bug_refs" not in triage_agent_doc or "recommended_investigation_paths" not in triage_agent_doc:
        findings.append("triage agent doc must define candidate_bug_refs and recommended_investigation_paths outputs")
    if "candidate_bug_refs" not in triage_skill or "recommended_investigation_paths" not in triage_skill:
        findings.append("triage skill must expose candidate_bug_refs and recommended_investigation_paths")
    if "BugCard/BugFull" not in triage_skill:
        findings.append("triage skill must mention BugCard/BugFull history matching")
    if "candidate_bug_refs" not in main_skill or "recommended_investigation_paths" not in main_skill:
        findings.append("rdc-debugger skill must define consumption of triage routing hints")
    if "不参与当前 run 的前置方向建议" not in curator_agent_doc or "反向做 dispatch" not in curator_agent_doc:
        findings.append("curator agent doc must forbid front-loaded routing and dispatch feedback loops")
    if "不参与当前 run 的前置方向建议" not in curator_skill:
        findings.append("curator skill must keep curator in post-run knowledge curation only")
    if "统一走已配置的 MCP server" in claude_code_readme:
        findings.append("claude-code README must not declare MCP as the only default path")
    for text in (codex_readme, codex_agents):
        if "host_delegation_policy = platform_managed" not in text or "host_delegation_fallback = none" not in text:
            findings.append("codex docs must declare platform-managed native specialist dispatch semantics")
        if "single_agent_by_user" not in text or "BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT" not in text:
            findings.append("codex docs must explain explicit single-agent mode and specialist feedback timeout semantics")
        if "runtime_owner + shared harness guard + audit artifacts" not in text:
            findings.append("codex docs must describe runtime_owner + shared harness guard + audit artifacts enforcement")
        if ".codex/runtime_guard.py" not in text:
            findings.append("codex docs must reference the runtime_guard.py enforcement entrypoint")

    legacy_capture_markers = (
        "当前对话提交至少一份 `.rdc`",
        "当前对话提交一份或多份 `.rdc`",
        "当前对话中提交一份或多份 `.rdc`",
        "当前对话上传 `.rdc` 为准",
        "请先在当前对话中提交一份或多份 `.rdc` 文件",
    )
    for path in [root / "README.md", *list((root / "common").rglob("*.md")), *list((root / "platforms").rglob("*.md"))]:
        text = path.read_text(encoding="utf-8-sig")
        for marker in legacy_capture_markers:
            if marker in text:
                findings.append(f"legacy capture intake wording must not remain in {path}: {marker}")
    manual_prestaging_markers = (
        "必须手工把 `.rdc` 预放",
        "需要手工把 `.rdc` 预放",
        "用户手工把 `.rdc` 预放到 `workspace/`",
        "用户手工把文件预放到 `workspace/`",
    )
    for path in (root / "platforms").rglob("*.md"):
        text = path.read_text(encoding="utf-8-sig")
        for marker in manual_prestaging_markers:
            if marker in text:
                findings.append(f"platform docs must not require manual workspace pre-staging: {path}: {marker}")

    manus_forbidden_markers = (
        "不提供 native `MCP` 入口",
        "不提供 native MCP 入口",
        "不得假设宿主侧存在可直接连接的 MCP server",
        "MCP not supported",
    )
    for marker in manus_forbidden_markers:
        if marker in manus_readme or marker in manus_entrypoints or marker in manus_workflow:
            findings.append(f"manus docs must not contain legacy MCP denial: {marker}")

    return findings


def _model_routing_findings(root: Path) -> list[str]:
    findings: list[str] = []
    routing = _read_json(root / "common" / "config" / "model_routing.json")
    role_policy = _read_json(root / "common" / "config" / "role_policy.json")
    caps = _read_json(root / "common" / "config" / "platform_capabilities.json")
    manifest = _read_json(root / "common" / "config" / "role_manifest.json")

    cap_platforms = caps.get("platforms") or {}
    routing_profiles = routing.get("profiles") or {}
    role_profiles = routing.get("role_profiles") or {}
    policy_profiles = role_policy.get("model_profiles") or {}
    policy_roles = role_policy.get("roles") or {}
    manifest_roles = {row["agent_id"]: row for row in manifest.get("roles") or []}
    declared_classes = routing.get("platform_classes") or {}

    if "global_requirements" not in routing:
        findings.append("model_routing.json missing global_requirements")

    class_members: set[str] = set()
    for class_name, platforms in declared_classes.items():
        if not isinstance(platforms, list):
            findings.append(f"model_routing.json platform_classes.{class_name} must be a list")
            continue
        class_members.update(str(item) for item in platforms)
    if class_members and class_members != set(cap_platforms):
        findings.append("model_routing.json platform_classes do not cover exactly the platform_capabilities platforms")

    for profile_name, profile in sorted(policy_profiles.items()):
        if "platform_models" in profile:
            findings.append(f"role_policy.json model_profiles.{profile_name} still contains platform_models")

    if set(role_profiles) != set(manifest_roles):
        findings.append("model_routing.json role_profiles keys differ from role_manifest roles")
    if set(policy_roles) != set(manifest_roles):
        findings.append("role_policy.json role keys differ from role_manifest roles")

    for agent_id, profile_name in sorted(role_profiles.items()):
        if profile_name not in routing_profiles:
            findings.append(f"model_routing.json missing profile '{profile_name}' for role {agent_id}")
            continue
        if agent_id not in policy_roles:
            findings.append(f"role_policy.json missing role policy for {agent_id}")
            continue
        policy_profile = str(policy_roles[agent_id].get("model_profile", "")).strip()
        if policy_profile != profile_name:
            findings.append(f"{agent_id}: role_policy model_profile mismatch ({policy_profile} != {profile_name})")

    for profile_name, profile in sorted(routing_profiles.items()):
        routing_map = profile.get("platform_rendering") or {}
        if set(routing_map) != set(cap_platforms):
            findings.append(f"{profile_name}: platform_rendering keys differ from platform_capabilities platforms")
            continue
        for platform_key, platform_caps in sorted(cap_platforms.items()):
            routed_model = str(routing_map.get(platform_key, "")).strip()
            if _platform_is_inherit_only(platform_caps):
                if routed_model != "inherit":
                    findings.append(f"{profile_name}: inherit-only platform {platform_key} must route to inherit, got '{routed_model}'")
            elif not routed_model or routed_model == "inherit":
                findings.append(f"{profile_name}: platform {platform_key} must have an explicit rendered model")

    rendered_platforms = ["code-buddy", "claude-code", "copilot-cli", "copilot-ide", "cursor", "codex"]
    for platform_key in rendered_platforms:
        platform_caps = cap_platforms.get(platform_key) or {}
        if not _platform_renders_per_agent_model(platform_caps):
            findings.append(f"{platform_key}: expected rendered per-agent model support is missing from platform_capabilities")
            continue
        for agent_id in sorted(manifest_roles):
            expected = _expected_rendered_model(root, platform_key, agent_id)
            if expected is None:
                continue
            path, expected_model = expected
            if not path.exists():
                findings.append(f"{platform_key}: rendered agent file missing: {path}")
                continue
            if platform_key == "codex":
                actual_model = _toml_string(path, "model")
            else:
                actual_model = _frontmatter_string(path, "model")
            if actual_model != expected_model:
                findings.append(f"{platform_key}: {agent_id} rendered model mismatch ({actual_model} != {expected_model})")

    return findings


def _compliance_findings(root: Path) -> list[str]:
    findings: list[str] = []
    compliance = _read_json(root / "common" / "config" / "framework_compliance.json")
    caps = _read_json(root / "common" / "config" / "platform_capabilities.json")
    platforms = compliance.get("platforms") or {}
    cap_platforms = caps.get("platforms") or {}
    entry_model = compliance.get("entry_model") or {}

    if str(entry_model.get("public_entry_skill", "")).strip() != "rdc-debugger":
        findings.append("framework_compliance.json entry_model.public_entry_skill must be rdc-debugger")
    if "orchestration_role" in entry_model:
        findings.append("framework_compliance.json entry_model.orchestration_role must not remain")
    if "notes/hypothesis_board.yaml" not in str(entry_model.get("panel_state_source", "")).strip():
        findings.append("framework_compliance.json entry_model.panel_state_source must point to notes/hypothesis_board.yaml")

    if set(platforms) != set(cap_platforms):
        findings.append("framework_compliance.json and platform_capabilities.json platform keys differ")

    for key, rules in sorted(platforms.items()):
        platform_caps = cap_platforms.get(key)
        if not isinstance(platform_caps, dict):
            findings.append(f"missing platform_capabilities entry for {key}")
            continue

        default_entry_mode = str(platform_caps.get("default_entry_mode", "")).strip()
        allowed_entry_modes = list(platform_caps.get("allowed_entry_modes") or [])
        if default_entry_mode not in {"cli", "mcp"}:
            findings.append(f"{key}: default_entry_mode must be cli or mcp")
        if not allowed_entry_modes or any(mode not in {"cli", "mcp"} for mode in allowed_entry_modes):
            findings.append(f"{key}: allowed_entry_modes must only contain cli/mcp")
        if default_entry_mode and default_entry_mode not in allowed_entry_modes:
            findings.append(f"{key}: default_entry_mode must be included in allowed_entry_modes")

        sub_agent_mode = str(platform_caps.get("sub_agent_mode", "")).strip()
        peer_communication = str(platform_caps.get("peer_communication", "")).strip()
        agent_description_mode = str(platform_caps.get("agent_description_mode", "")).strip()
        dispatch_topology = str(platform_caps.get("dispatch_topology", "")).strip()
        specialist_dispatch_requirement = str(platform_caps.get("specialist_dispatch_requirement", "")).strip()
        host_delegation_policy = str(platform_caps.get("host_delegation_policy", "")).strip()
        host_delegation_fallback = str(platform_caps.get("host_delegation_fallback", "")).strip()
        local_live_runtime_policy = str(platform_caps.get("local_live_runtime_policy", "")).strip()
        remote_live_runtime_policy = str(platform_caps.get("remote_live_runtime_policy", "")).strip()
        if sub_agent_mode not in {"team_agents", "puppet_sub_agents", "instruction_only_sub_agents"}:
            findings.append(f"{key}: invalid sub_agent_mode")
        if peer_communication not in {"direct", "via_main_agent", "none"}:
            findings.append(f"{key}: invalid peer_communication")
        if agent_description_mode not in {"independent_files", "spawn_instruction_only"}:
            findings.append(f"{key}: invalid agent_description_mode")
        if dispatch_topology not in {"mesh", "hub_and_spoke", "workflow_serial"}:
            findings.append(f"{key}: invalid dispatch_topology")
        if specialist_dispatch_requirement not in {"required"}:
            findings.append(f"{key}: invalid specialist_dispatch_requirement")
        if host_delegation_policy not in {"platform_managed"}:
            findings.append(f"{key}: invalid host_delegation_policy")
        if host_delegation_fallback not in {"native", "none"}:
            findings.append(f"{key}: invalid host_delegation_fallback")
        if local_live_runtime_policy not in {"multi_context_multi_owner", "multi_context_orchestrated", "single_runtime_owner"}:
            findings.append(f"{key}: invalid local_live_runtime_policy")
        if remote_live_runtime_policy != "single_runtime_owner":
            findings.append(f"{key}: remote_live_runtime_policy must be single_runtime_owner")

        expected_mode = str(rules.get("coordination_mode", "")).strip()
        actual_mode = str(platform_caps.get("coordination_mode", "")).strip()
        if expected_mode != actual_mode:
            findings.append(f"{key}: coordination_mode mismatch ({expected_mode} != {actual_mode})")

        if actual_mode == "concurrent_team":
            if sub_agent_mode != "team_agents" or peer_communication != "direct" or dispatch_topology != "mesh":
                findings.append(f"{key}: concurrent_team requires team_agents + direct + mesh")
            if specialist_dispatch_requirement != "required" or host_delegation_policy != "platform_managed" or host_delegation_fallback != "native":
                findings.append(f"{key}: concurrent_team requires required/platform_managed/native delegation defaults")
            if local_live_runtime_policy != "multi_context_multi_owner":
                findings.append(f"{key}: concurrent_team requires multi_context_multi_owner local policy")
        elif actual_mode == "staged_handoff":
            if sub_agent_mode != "puppet_sub_agents" or peer_communication != "via_main_agent" or dispatch_topology != "hub_and_spoke":
                findings.append(f"{key}: staged_handoff requires puppet_sub_agents + via_main_agent + hub_and_spoke")
            if specialist_dispatch_requirement != "required" or host_delegation_policy != "platform_managed" or host_delegation_fallback != "none":
                findings.append(f"{key}: staged_handoff requires required/platform_managed/none delegation defaults")
            if local_live_runtime_policy != "multi_context_orchestrated":
                findings.append(f"{key}: staged_handoff requires multi_context_orchestrated local policy")
        elif actual_mode == "workflow_stage":
            if sub_agent_mode != "instruction_only_sub_agents" or peer_communication != "none" or dispatch_topology != "workflow_serial":
                findings.append(f"{key}: workflow_stage requires instruction_only_sub_agents + none + workflow_serial")
            if agent_description_mode != "spawn_instruction_only":
                findings.append(f"{key}: workflow_stage requires spawn_instruction_only agent descriptions")
            if specialist_dispatch_requirement != "required" or host_delegation_policy != "platform_managed" or host_delegation_fallback != "none":
                findings.append(f"{key}: workflow_stage requires required/platform_managed/none delegation defaults")

        enforcement_mode = str(rules.get("enforcement_mode", "")).strip()
        hooks_supported = _surface_supported(platform_caps, "hooks")
        if enforcement_mode not in {"native_hook_harness", "pseudo_hook_harness", "no_hook_audit", "runtime_owner_gate_loop"}:
            findings.append(f"{key}: invalid enforcement_mode")
        if enforcement_mode == "native_hook_harness" and not hooks_supported:
            findings.append(f"{key}: native_hook_harness requires hooks support")
        if enforcement_mode == "pseudo_hook_harness" and hooks_supported:
            findings.append(f"{key}: pseudo_hook_harness should not claim native hooks support")
        if enforcement_mode == "no_hook_audit" and actual_mode != "workflow_stage" and key not in {"codex_plugin"}:
            findings.append(f"{key}: no_hook_audit requires workflow_stage or explicit plugin wrapper handling")
        if enforcement_mode == "runtime_owner_gate_loop" and str(platform_caps.get("enforcement_layer", "")).strip() != "runtime_owner":
            findings.append(f"{key}: runtime_owner_gate_loop requires enforcement_layer=runtime_owner")

        for surface in rules.get("required_surfaces") or []:
            if not _surface_supported(platform_caps, str(surface)):
                findings.append(f"{key}: required surface '{surface}' is not supported by platform_capabilities")

        for rel in platform_caps.get("required_paths") or []:
            path = root / rel
            if not path.exists():
                findings.append(f"{key}: required path missing: {path}")

        if rules.get("workflow_required") and actual_mode != "workflow_stage":
            findings.append(f"{key}: workflow_required=true but coordination_mode is not workflow_stage")

    expected_cli_first = {"code-buddy", "claude-code", "copilot-cli", "copilot-ide", "codex", "cursor"}
    actual_cli_first = {
        key for key, row in cap_platforms.items() if str(row.get("default_entry_mode", "")).strip() == "cli"
    }
    if actual_cli_first != expected_cli_first:
        findings.append("platform_capabilities.json CLI-first platform set mismatch")

    expected_mcp_only = {"claude-desktop", "manus"}
    actual_mcp_only = {
        key for key, row in cap_platforms.items() if list(row.get("allowed_entry_modes") or []) == ["mcp"]
    }
    if actual_mcp_only != expected_mcp_only:
        findings.append("platform_capabilities.json MCP-only platform set mismatch")

    live_sessions = root / "common" / "knowledge" / "library" / "sessions"
    allowed = set(compliance["runtime_artifact_contract"]["allowed_live_library_session_entries"])
    if live_sessions.is_dir():
        for child in live_sessions.iterdir():
            if child.name in allowed:
                continue
            if child.is_dir() and not any(child.iterdir()):
                continue
            if child.name not in allowed:
                findings.append(f"live library sessions contains example or unexpected entry: {child}")

    return findings


def _spec_store_findings(root: Path) -> list[str]:
    findings: list[str] = []
    spec_root = root / "common" / "knowledge" / "spec"
    required = [
        spec_root / "README.md",
        spec_root / "registry" / "active_manifest.yaml",
        spec_root / "registry" / "spec_registry.yaml",
        spec_root / "policy" / "evolution_policy.yaml",
        spec_root / "negative_memory.yaml",
        spec_root / "ledger" / "evolution_ledger.jsonl",
    ]
    forbidden = [
        spec_root / "skills",
        spec_root / "invariants",
        spec_root / "taxonomy",
        root / "common" / "docs" / "sop_extraction_guide.md",
    ]

    for path in required:
        if not path.exists():
            findings.append(f"missing versioned spec store path: {path}")

    for path in forbidden:
        if path.exists():
            findings.append(f"legacy spec path must not exist: {path}")

    if findings:
        return findings

    manifest = _read_yaml(spec_root / "registry" / "active_manifest.yaml")
    registry = _read_yaml(spec_root / "registry" / "spec_registry.yaml")
    families = manifest.get("families") or {}
    registry_families = registry.get("families") or {}
    if set(families) != set(registry_families):
        findings.append("active_manifest and spec_registry family keys differ")
        return findings

    for family, entry in sorted(families.items()):
        if not isinstance(entry, dict):
            findings.append(f"active_manifest family entry must be an object: {family}")
            continue
        object_path = root / str(entry.get("object_path", "")).replace("/", "\\")
        if not object_path.is_file():
            findings.append(f"{family}: active object missing: {object_path}")
            continue
        obj = _read_yaml(object_path)
        if not isinstance(obj, dict):
            findings.append(f"{family}: active object must be a YAML object")
            continue
        payload_path = root / str(obj.get("payload_path", "")).replace("/", "\\")
        if not payload_path.is_file():
            findings.append(f"{family}: active payload missing: {payload_path}")

    return findings


def _intake_contract_findings(root: Path) -> list[str]:
    findings: list[str] = []
    required = [
        root / "common" / "docs" / "intake" / "README.md",
        root / "common" / "docs" / "intake" / "USER_PROMPT_TEMPLATE.md",
        root / "common" / "docs" / "intake" / "USER_PROMPT_MINIMAL.md",
        root / "common" / "docs" / "intake" / "examples" / "example_single.md",
        root / "common" / "docs" / "intake" / "examples" / "example_cross_device.md",
        root / "common" / "docs" / "intake" / "examples" / "example_regression.md",
        root / "common" / "hooks" / "validators" / "hypothesis_board_validator.py",
        root / "common" / "hooks" / "schemas" / "hypothesis_board_schema.yaml",
        root / "common" / "hooks" / "validators" / "intake_validator.py",
        root / "common" / "hooks" / "schemas" / "intake_case_input_schema.yaml",
        root / "common" / "hooks" / "schemas" / "fix_verification_schema.yaml",
    ]
    for path in required:
        if not path.exists():
            findings.append(f"missing intake contract path: {path}")
    return findings


def _claude_settings_findings(root: Path) -> list[str]:
    findings: list[str] = []
    settings_path = root / "platforms" / "claude-code" / ".claude" / "settings.json"
    if not settings_path.is_file():
        findings.append(f"missing Claude Code settings: {settings_path}")
        return findings

    payload = _read_json(settings_path)
    hooks = payload.get("hooks") or {}
    if not isinstance(hooks, dict):
        findings.append("claude-code settings hooks must be an object")
        return findings

    for event_name, entries in hooks.items():
        if not isinstance(entries, list):
            findings.append(f"claude-code settings hooks.{event_name} must be a list")
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                findings.append(f"claude-code settings hooks.{event_name}[{index}] must be an object")
                continue
            matcher = entry.get("matcher")
            if matcher is not None and not isinstance(matcher, str):
                findings.append(
                    f"claude-code settings hooks.{event_name}[{index}].matcher must be a string"
                )
    return findings


def _claude_code_agent_findings(root: Path) -> list[str]:
    findings: list[str] = []
    manifest = _read_json(root / "common" / "config" / "role_manifest.json")
    role_policy = _read_json(root / "common" / "config" / "role_policy.json")
    settings = _read_json(root / "platforms" / "claude-code" / ".claude" / "settings.json")

    roles = manifest.get("roles") or []
    role_rows = role_policy.get("roles") or {}
    tool_policies = role_policy.get("tool_policies") or {}
    claude_agents_root = root / "platforms" / "claude-code" / ".claude" / "agents"
    actual_agent = str(settings.get("agent", "")).strip()
    if actual_agent:
        findings.append("claude-code settings must not bind a default debugger subagent")

    for role in roles:
        platform_file = (role.get("platform_files") or {}).get("claude-code")
        if not platform_file:
            continue
        expected_name = _claude_code_subagent_name(role)
        if not expected_name:
            findings.append(f"{role.get('agent_id')}: missing platform_subagent_names.claude-code")
            continue

        path = claude_agents_root / platform_file
        if not path.is_file():
            findings.append(f"claude-code agent file missing: {path}")
            continue

        actual_name = _frontmatter_string(path, "name")
        if actual_name != expected_name:
            findings.append(f"claude-code {role.get('agent_id')} name mismatch ({actual_name} != {expected_name})")

        description = _frontmatter_string(path, "description")
        if not description:
            findings.append(f"claude-code {role.get('agent_id')} missing description")

    triage_role = next((role for role in roles if role.get("agent_id") == "triage_agent"), None)
    if triage_role:
        triage_path = claude_agents_root / str((triage_role.get("platform_files") or {}).get("claude-code", ""))
        if not triage_path.is_file():
            findings.append(f"claude-code triage_agent file missing: {triage_path}")
        else:
            triage_tools = _frontmatter_string(triage_path, "tools")
            if not triage_tools:
                findings.append("claude-code triage_agent must use an explicit tools allowlist")
            if triage_tools and ("Bash" in triage_tools or "Agent(" in triage_tools):
                findings.append("claude-code triage_agent must not expose Bash or Agent")

    for role in roles:
        agent_id = str(role.get("agent_id", "")).strip()
        policy_name = str((role_rows.get(agent_id) or {}).get("tool_policy", "")).strip()
        policy = tool_policies.get(policy_name) or {}
        allow_live_tools = bool(policy.get("allow_live_tools"))
        if not allow_live_tools:
            continue
        platform_file = (role.get("platform_files") or {}).get("claude-code")
        if not platform_file:
            continue
        path = claude_agents_root / platform_file
        if not path.is_file():
            continue
        disallowed = _frontmatter_string(path, "disallowedTools")
        if not disallowed or "Bash" not in disallowed or "Agent" not in disallowed:
            findings.append(f"claude-code {agent_id} must deny Bash and Agent fallback")

    return findings


def _write_scope_findings(root: Path) -> list[str]:
    findings: list[str] = []
    compliance = _read_json(root / "common" / "config" / "framework_compliance.json")
    role_policy = _read_json(root / "common" / "config" / "role_policy.json")
    scope_contract = (compliance.get("runtime_artifact_contract") or {}).get("write_scope_paths") or {}
    role_rows = role_policy.get("roles") or {}

    required_scopes = {
        "workspace_control",
        "workspace_notes",
        "session_signoff",
        "workspace_reports",
        "session_artifacts",
        "knowledge_library",
    }
    missing_scopes = required_scopes - set(scope_contract)
    if missing_scopes:
        findings.append(f"framework_compliance.json missing write_scope_paths entries: {sorted(missing_scopes)}")

    expected_role_scopes = {
        "triage_agent": {"workspace_notes"},
        "capture_repro_agent": {"workspace_notes"},
        "pass_graph_pipeline_agent": {"workspace_notes"},
        "pixel_forensics_agent": {"workspace_notes"},
        "shader_ir_agent": {"workspace_notes"},
        "driver_device_agent": {"workspace_notes"},
        "skeptic_agent": {"session_signoff"},
        "curator_agent": {"workspace_reports", "session_artifacts", "knowledge_library"},
    }

    for agent_id, row in sorted(role_rows.items()):
        if "writable_artifacts" in row:
            findings.append(f"{agent_id}: writable_artifacts must not remain in role_policy.json")
        actual_scopes = set(row.get("write_scopes") or [])
        if agent_id in expected_role_scopes and actual_scopes != expected_role_scopes[agent_id]:
            findings.append(f"{agent_id}: write_scopes mismatch ({sorted(actual_scopes)} != {sorted(expected_role_scopes[agent_id])})")
        undefined_scopes = actual_scopes - set(scope_contract)
        if undefined_scopes:
            findings.append(f"{agent_id}: write_scopes reference undefined contract scopes {sorted(undefined_scopes)}")

    doc_checks = [
        ("rdc-debugger", root / "common" / "skills" / "rdc-debugger" / "SKILL.md", ["case_input.yaml", "case_id", "run_id", "hypothesis_board.yaml"]),
        ("triage_agent", root / "common" / "agents" / "02_triage_taxonomy.md", ["runs/<run_id>/notes/"]),
        ("capture_repro_agent", root / "common" / "agents" / "03_capture_repro.md", ["runs/<run_id>/notes/"]),
        ("pass_graph_pipeline_agent", root / "common" / "agents" / "04_pass_graph_pipeline.md", ["runs/<run_id>/notes/"]),
        ("pixel_forensics_agent", root / "common" / "agents" / "05_pixel_value_forensics.md", ["runs/<run_id>/notes/"]),
        ("shader_ir_agent", root / "common" / "agents" / "06_shader_ir.md", ["runs/<run_id>/notes/"]),
        ("driver_device_agent", root / "common" / "agents" / "07_driver_device.md", ["runs/<run_id>/notes/"]),
        ("skeptic_agent", root / "common" / "agents" / "08_skeptic.md", ["skeptic_signoff.yaml"]),
        (
            "curator_agent",
            root / "common" / "agents" / "09_report_knowledge_curator.md",
            ["reports/report.md", "reports/visual_report.html", "session_evidence.yaml", "action_chain.jsonl", "common/knowledge/library/bugcards/"],
        ),
    ]
    for agent_id, path, required_markers in doc_checks:
        if not path.is_file():
            findings.append(f"missing agent contract doc: {path}")
            continue
        text = path.read_text(encoding="utf-8-sig")
        for marker in required_markers:
            if marker not in text:
                findings.append(f"{agent_id}: agent contract missing write-scope marker '{marker}'")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate debugger repo")
    parser.add_argument("--strict", action="store_true", help="return non-zero when findings exist")
    args = parser.parse_args()

    root = _root()
    commands = [
        [sys.executable, str(root / "scripts" / "sync_platform_scaffolds.py"), "--check"],
        [sys.executable, str(root / "scripts" / "validate_platform_layout.py"), "--strict"],
        [sys.executable, str(root / "scripts" / "validate_tool_contract.py"), "--mode", "source", "--strict"],
    ]

    findings: list[str] = []
    for command in commands:
        proc = _run(command, root.parent)
        _print_proc(proc)
        if proc.returncode != 0:
            findings.append(f"command failed: {' '.join(command)}")

    findings.extend(_compliance_findings(root))
    findings.extend(_spec_store_findings(root))
    findings.extend(_intake_contract_findings(root))
    findings.extend(_model_routing_findings(root))
    findings.extend(_role_manifest_findings(root))
    findings.extend(_platform_wrapper_path_findings(root))
    findings.extend(_doc_contract_findings(root))
    findings.extend(_claude_settings_findings(root))
    findings.extend(_claude_code_agent_findings(root))
    findings.extend(_write_scope_findings(root))

    if findings:
        print("[debugger repo findings]")
        for row in findings:
            print(f" - {row}")
        return 1 if args.strict else 0

    print("debugger repo validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
