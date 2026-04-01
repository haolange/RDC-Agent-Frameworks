from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEBUGGER_ROOT = REPO_ROOT / "debugger"


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class RepoBaselineValidationTests(unittest.TestCase):
    def test_doc_contract_markers_present(self) -> None:
        core = (DEBUGGER_ROOT / "common" / "AGENT_CORE.md").read_text(encoding="utf-8-sig")
        skill = (DEBUGGER_ROOT / "common" / "skills" / "rdc-debugger" / "SKILL.md").read_text(encoding="utf-8-sig")
        self.assertIn("PROCESS_DEVIATION_MAIN_AGENT_OVERREACH", core)
        self.assertIn("BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT", core)
        self.assertIn("final_audit / render_user_verdict", skill)
        self.assertIn("reports/visual_report.html", skill)

    def test_platform_wrappers_do_not_escape_platform_roots(self) -> None:
        validator = _load_module(
            DEBUGGER_ROOT / "scripts" / "validate_debugger_repo.py",
            "validate_debugger_repo_platform_paths_module",
        )
        findings = validator._platform_wrapper_path_findings(DEBUGGER_ROOT)
        self.assertEqual(findings, [])

    def test_machine_consumed_common_and_platform_files_are_utf8_without_bom(self) -> None:
        exts = {".md", ".mdc", ".json", ".toml", ".yaml", ".yml"}
        offenders: list[str] = []
        for root in (DEBUGGER_ROOT / "common", DEBUGGER_ROOT / "platforms"):
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in exts:
                    continue
                if path.read_bytes().startswith(b"\xef\xbb\xbf"):
                    offenders.append(str(path.relative_to(DEBUGGER_ROOT)).replace("\\", "/"))
        self.assertEqual(offenders, [])


    def test_entry_mode_contract_is_documented_in_matrix(self) -> None:
        text = (DEBUGGER_ROOT / "common" / "docs" / "platform-capability-matrix.md").read_text(encoding="utf-8-sig")
        self.assertIn("Default Entry", text)
        self.assertIn("Allowed Entry Modes", text)
        self.assertIn("| Claude Code |", text)
        self.assertIn("CLI, MCP", text)

    def test_rdc_debugger_skill_declares_intent_gate_contract(self) -> None:
        text = (DEBUGGER_ROOT / "common" / "skills" / "rdc-debugger" / "SKILL.md").read_text(encoding="utf-8-sig")
        for marker in (
            "intent_gate",
            "primary_completion_question",
            "requested_artifact",
            "dominant_operation",
            "ab_role",
            "拒绝进入 `debugger`",
            "多轮澄清",
        ):
            self.assertIn(marker, text)

    def test_triage_knowledge_contract_is_documented(self) -> None:
        agent_text = (DEBUGGER_ROOT / "common" / "agents" / "02_triage_taxonomy.md").read_text(encoding="utf-8-sig")
        skill_text = (DEBUGGER_ROOT / "common" / "skills" / "triage-taxonomy" / "SKILL.md").read_text(encoding="utf-8-sig")
        for text in (agent_text, skill_text):
            self.assertIn("knowledge/library/bugcards/", text)
            self.assertIn("knowledge/library/bugfull/", text)
            self.assertIn("candidate_bug_refs", text)
            self.assertIn("recommended_investigation_paths", text)
        self.assertIn("不得直接当作当前 run 的根因结论", agent_text)

    def test_curator_is_documented_as_post_run_knowledge_curation(self) -> None:
        agent_text = (DEBUGGER_ROOT / "common" / "agents" / "09_report_knowledge_curator.md").read_text(encoding="utf-8-sig")
        skill_text = (DEBUGGER_ROOT / "common" / "skills" / "report-knowledge-curator" / "SKILL.md").read_text(encoding="utf-8-sig")
        self.assertIn("不参与当前 run 的前置方向建议", agent_text)
        self.assertIn("不读取 triage 的知识匹配结果来反向做 specialist dispatch", agent_text)
        self.assertIn("reports/visual_report.html", skill_text)

    def test_platform_wrappers_mirror_triage_and_curator_knowledge_boundaries(self) -> None:
        codex_triage = (DEBUGGER_ROOT / "platforms" / "codex" / ".codex" / "skills" / "triage-taxonomy" / "SKILL.md").read_text(encoding="utf-8-sig")
        codex_curator = (DEBUGGER_ROOT / "platforms" / "codex" / ".codex" / "skills" / "report-knowledge-curator" / "SKILL.md").read_text(encoding="utf-8-sig")
        claude_triage = (DEBUGGER_ROOT / "platforms" / "claude-code" / ".claude" / "agents" / "02_triage_taxonomy.md").read_text(encoding="utf-8")
        claude_curator = (DEBUGGER_ROOT / "platforms" / "claude-code" / ".claude" / "agents" / "09_report_knowledge_curator.md").read_text(encoding="utf-8")

        for text in (codex_triage, claude_triage):
            self.assertIn("BugCard/BugFull", text)
            self.assertIn("candidate_bug_refs", text)
            self.assertIn("recommended_investigation_paths", text)
        for text in (codex_curator, claude_curator):
            self.assertIn("proposal", text)
            self.assertIn("不参与当前 run 的前置方向建议", text)

    def test_capture_intake_docs_allow_upload_or_accessible_path(self) -> None:
        core_text = (DEBUGGER_ROOT / "common" / "AGENT_CORE.md").read_text(encoding="utf-8-sig")
        self.assertIn("在当前对话上传", core_text)
        self.assertIn("文件路径", core_text)

    def test_shader_ir_agent_uses_event_bound_shader_queries_and_truthful_debug_failures(self) -> None:
        text = (DEBUGGER_ROOT / "common" / "agents" / "06_shader_ir.md").read_text(encoding="utf-8-sig")
        self.assertIn('rd.pipeline.get_shader(session_id=<session_id>, event_id=<first_bad_event>, stage="PS")', text)
        self.assertIn("data.shader.shader_id", text)
        self.assertIn("failure_stage", text)
        self.assertIn("failure_reason", text)
        self.assertIn("attempts", text)
        self.assertIn("结构化 blocked/runtime failure", text)

    def test_rdc_debugger_docs_declare_minimal_noninteractive_preflight(self) -> None:
        skill_text = (DEBUGGER_ROOT / "common" / "skills" / "rdc-debugger" / "SKILL.md").read_text(encoding="utf-8-sig")
        intake_text = (DEBUGGER_ROOT / "common" / "docs" / "intake" / "README.md").read_text(encoding="utf-8-sig")
        for marker in ("minimal_non_interactive", "claude -p", "bounded readiness output"):
            self.assertIn(marker, skill_text)
        self.assertIn("rdc-debugger", intake_text)
        self.assertIn("case/run", intake_text)

    def test_rdc_debugger_contract_requires_immediate_case_run_initialization(self) -> None:
        text = (DEBUGGER_ROOT / "common" / "skills" / "rdc-debugger" / "SKILL.md").read_text(encoding="utf-8-sig")
        for marker in (
            "Immediate Case/Run Initialization",
            "`intent_gate.decision = debugger`",
            "preflight passed",
            "artifacts/entry_gate.yaml",
            "`session.goal` is normalized",
            "standalone tools-layer capture open is not sufficient",
            "../workspace/cases/<case_id>/runs/<run_id>/notes/hypothesis_board.yaml",
            "rd.export.texture",
        ):
            self.assertIn(marker, text)

    def test_scaffold_expected_paths_cover_codex(self) -> None:
        scaffold = _load_module(DEBUGGER_ROOT / "scripts" / "sync_platform_scaffolds.py", "sync_platform_scaffolds_module")
        ctx = scaffold.load_context(DEBUGGER_ROOT)
        expected = scaffold.expected_files(ctx, "codex")
        self.assertIn(DEBUGGER_ROOT / "platforms" / "codex" / ".codex" / "config.toml", expected)
        self.assertIn(DEBUGGER_ROOT / "platforms" / "codex" / ".codex" / "runtime_guard.py", expected)
        self.assertIn(DEBUGGER_ROOT / "platforms" / "codex" / ".codex" / "agents" / "triage_agent.toml", expected)
        self.assertIn(DEBUGGER_ROOT / "platforms" / "codex" / ".codex" / "skills" / "rdc-debugger" / "SKILL.md", expected)

    def test_claude_settings_matchers_are_strings(self) -> None:
        settings = json.loads(
            (DEBUGGER_ROOT / "platforms" / "claude-code" / ".claude" / "settings.json").read_text(
                encoding="utf-8-sig"
            )
        )
        hooks = settings.get("hooks") or {}

        for event_name, entries in hooks.items():
            self.assertIsInstance(entries, list, event_name)
            for entry in entries:
                self.assertIsInstance(entry.get("matcher"), str, f"{event_name} matcher must be string")

    def test_default_platform_configs_do_not_pre_register_mcp(self) -> None:
        claude_settings = json.loads(
            (DEBUGGER_ROOT / "platforms" / "claude-code" / ".claude" / "settings.json").read_text(
                encoding="utf-8-sig"
            )
        )
        codex_config = (DEBUGGER_ROOT / "platforms" / "codex" / ".codex" / "config.toml").read_text(encoding="utf-8-sig")
        self.assertEqual((claude_settings.get("mcpServers") or {}), {})
        self.assertNotIn("[mcp_servers.renderdoc-platform-mcp]", codex_config)
        self.assertTrue((DEBUGGER_ROOT / "platforms" / "claude-code" / ".claude" / "settings.mcp.opt-in.json").is_file())
        self.assertTrue((DEBUGGER_ROOT / "platforms" / "codex" / ".codex" / "config.mcp.opt-in.toml").is_file())

    def test_codex_coordination_mode_is_consistent(self) -> None:
        compliance = json.loads(
            (DEBUGGER_ROOT / "common" / "config" / "framework_compliance.json").read_text(encoding="utf-8-sig")
        )
        capabilities = json.loads(
            (DEBUGGER_ROOT / "common" / "config" / "platform_capabilities.json").read_text(encoding="utf-8-sig")
        )

        self.assertEqual(
            compliance["platforms"]["codex"]["coordination_mode"],
            capabilities["platforms"]["codex"]["coordination_mode"],
        )
        self.assertEqual(capabilities["platforms"]["codex"]["coordination_mode"], "staged_handoff")

    def test_codex_docs_declare_intake_gate_before_handoff(self) -> None:
        readme = (DEBUGGER_ROOT / "platforms" / "codex" / "README.md").read_text(encoding="utf-8-sig")
        agents = (DEBUGGER_ROOT / "platforms" / "codex" / "AGENTS.md").read_text(encoding="utf-8-sig")
        for text in (readme, agents):
            self.assertIn(".codex/runtime_guard.py", text)
            self.assertIn("runtime_owner + shared harness guard + audit artifacts", text)
            self.assertIn("artifacts/entry_gate.yaml", text)
            self.assertIn("artifacts/intake_gate.yaml", text)
            self.assertIn("artifacts/runtime_topology.yaml", text)
            self.assertIn("capture import", text)
            self.assertIn("case/run bootstrap", text)

    def test_platform_capabilities_declare_mode_support_and_enforcement(self) -> None:
        capabilities = json.loads(
            (DEBUGGER_ROOT / "common" / "config" / "platform_capabilities.json").read_text(encoding="utf-8-sig")
        )
        snapshot = json.loads(
            (DEBUGGER_ROOT / "common" / "config" / "runtime_mode_truth.snapshot.json").read_text(encoding="utf-8-sig")
        )
        self.assertTrue((snapshot.get("modes") or {}).get("local_cli"))
        self.assertTrue((snapshot.get("modes") or {}).get("remote_mcp"))
        for row in (capabilities.get("platforms") or {}).values():
            self.assertIn(row.get("local_support"), {"verified", "degraded", "unsupported"})
            self.assertIn(row.get("remote_support"), {"verified", "serial_only", "unsupported"})
            self.assertIn(row.get("enforcement_layer"), {"native_hooks", "pseudo_hooks", "runtime_owner", "no_hooks"})
            self.assertEqual(row.get("remote_coordination_mode"), "single_runtime_owner")
            self.assertIn(row.get("sub_agent_mode"), {"team_agents", "puppet_sub_agents", "instruction_only_sub_agents"})
            self.assertIn(row.get("peer_communication"), {"direct", "via_main_agent", "none"})
            self.assertIn(row.get("agent_description_mode"), {"independent_files", "spawn_instruction_only", "skill_files"})
            self.assertIn(row.get("dispatch_topology"), {"mesh", "hub_and_spoke", "workflow_serial"})
            self.assertEqual(row.get("specialist_dispatch_requirement"), "required")
            self.assertEqual(row.get("host_delegation_policy"), "platform_managed")
            self.assertIn(row.get("host_delegation_fallback"), {"native", "none"})
            self.assertIn(row.get("local_live_runtime_policy"), {"multi_context_multi_owner", "multi_context_orchestrated", "single_runtime_owner"})
            self.assertEqual(row.get("remote_live_runtime_policy"), "single_runtime_owner")

    def test_codex_skill_wrapper_declares_single_agent_mode_and_feedback_contract(self) -> None:
        text = (DEBUGGER_ROOT / "platforms" / "codex" / ".codex" / "skills" / "rdc-debugger" / "SKILL.md").read_text(encoding="utf-8-sig")
        for marker in (
            ".codex/runtime_guard.py",
            "host_delegation_policy = platform_managed",
            "host_delegation_fallback = none",
            "single_agent_by_user",
            "BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT",
            "fallback_execution_mode=local_renderdoc_python",
            "waiting_for_specialist_brief",
            "dispatch-readiness",
            "final-audit",
        ):
            self.assertIn(marker, text)

    def test_claude_code_docs_declare_mode_matrix_and_runtime_topology(self) -> None:
        readme = (DEBUGGER_ROOT / "platforms" / "claude-code" / "README.md").read_text(encoding="utf-8-sig")
        agents = (DEBUGGER_ROOT / "platforms" / "claude-code" / "AGENTS.md").read_text(encoding="utf-8-sig")
        for text in (readme, agents):
            self.assertIn("local_support", text)
            self.assertIn("remote_support", text)
            self.assertIn("enforcement_layer", text)
            self.assertIn("artifacts/entry_gate.yaml", text)
            self.assertIn("artifacts/runtime_topology.yaml", text)

    def test_claude_code_default_agent_is_not_bound(self) -> None:
        validator = _load_module(DEBUGGER_ROOT / "scripts" / "validate_debugger_repo.py", "validate_debugger_repo_claude_agent_module")
        findings = validator._claude_code_agent_findings(DEBUGGER_ROOT)
        self.assertEqual(findings, [])

        settings = json.loads(
            (DEBUGGER_ROOT / "platforms" / "claude-code" / ".claude" / "settings.json").read_text(
                encoding="utf-8-sig"
            )
        )
        self.assertNotIn("agent", settings)

        compliance = json.loads(
            (DEBUGGER_ROOT / "common" / "config" / "framework_compliance.json").read_text(encoding="utf-8-sig")
        )
        self.assertEqual(compliance.get("entry_model", {}).get("public_entry_skill"), "rdc-debugger")
        self.assertNotIn("orchestration_role", compliance.get("entry_model", {}))

    def test_platform_role_skill_wrappers_keep_frontmatter_descriptors(self) -> None:
        for rel, skill_name in (
            ("platforms/codex/.codex/skills/capture-repro/SKILL.md", "capture-repro"),
            ("platforms/claude-code/.claude/skills/capture-repro/SKILL.md", "capture-repro"),
            ("platforms/code-buddy/skills/capture-repro/SKILL.md", "capture-repro"),
            ("platforms/copilot-cli/skills/capture-repro/SKILL.md", "capture-repro"),
        ):
            text = (DEBUGGER_ROOT / rel).read_text(encoding="utf-8-sig")
            self.assertTrue(text.startswith("---\n"), rel)
            self.assertIn(f"name: {skill_name}", text, rel)
            self.assertIn("description:", text, rel)
            self.assertIn("short-description:", text, rel)

    def test_wave1_platform_docs_include_generated_common_first_block(self) -> None:
        for rel in (
            "platforms/codex/README.md",
            "platforms/codex/AGENTS.md",
            "platforms/claude-code/README.md",
            "platforms/claude-code/AGENTS.md",
            "platforms/code-buddy/README.md",
            "platforms/code-buddy/AGENTS.md",
            "platforms/copilot-cli/README.md",
            "platforms/copilot-cli/AGENTS.md",
        ):
            text = (DEBUGGER_ROOT / rel).read_text(encoding="utf-8-sig")
            self.assertIn("BEGIN GENERATED COMMON-FIRST ADAPTER BLOCK", text)
            self.assertIn("adapter_readiness.json", text)

    def test_claude_code_docs_keep_cli_as_default_entry(self) -> None:
        readme = (DEBUGGER_ROOT / "platforms" / "claude-code" / "README.md").read_text(encoding="utf-8-sig")
        agents = (DEBUGGER_ROOT / "platforms" / "claude-code" / "AGENTS.md").read_text(encoding="utf-8-sig")
        entry = (DEBUGGER_ROOT / "platforms" / "claude-code" / ".claude" / "CLAUDE.md").read_text(encoding="utf-8-sig")
        self.assertIn("默认入口是 daemon-backed `CLI`", readme)
        self.assertIn("Claude Code 默认入口是 local-first `CLI`", agents)
        self.assertIn("默认入口模式是 local-first `CLI`", entry)

    def test_claude_code_workspace_docs_do_not_claim_capture_open_creates_case_run(self) -> None:
        workspace_text = (DEBUGGER_ROOT / "platforms" / "claude-code" / "workspace" / "README.md").read_text(encoding="utf-8-sig")
        cases_text = (DEBUGGER_ROOT / "platforms" / "claude-code" / "workspace" / "cases" / "README.md").read_text(encoding="utf-8-sig")

        self.assertIn("standalone `capture open`", workspace_text)
        self.assertIn("rdc-debugger` intake", workspace_text)
        self.assertIn("不要求用户手工把 `.rdc` 预放", workspace_text)
        self.assertIn("导入后的原始 `.rdc`", workspace_text)
        self.assertIn("standalone `capture open`", cases_text)
        self.assertIn("用户只负责提供 `.rdc`", cases_text)

    def test_platform_docs_do_not_limit_capture_to_current_dialog_submission(self) -> None:
        legacy_markers = (
            "当前对话提交至少一份 `.rdc`",
            "当前对话提交一份或多份 `.rdc`",
            "当前对话中提交一份或多份 `.rdc`",
            "当前对话上传 `.rdc` 为准",
        )
        platform_paths = list((DEBUGGER_ROOT / "platforms").rglob("README.md")) + list((DEBUGGER_ROOT / "platforms").rglob("AGENTS.md"))
        for path in platform_paths:
            text = path.read_text(encoding="utf-8-sig")
            for marker in legacy_markers:
                self.assertNotIn(marker, text, path)

    def test_claude_code_agent_frontmatter_has_names_and_descriptions(self) -> None:
        manifest = json.loads((DEBUGGER_ROOT / "common" / "config" / "role_manifest.json").read_text(encoding="utf-8-sig"))
        validator = _load_module(DEBUGGER_ROOT / "scripts" / "validate_debugger_repo.py", "validate_debugger_repo_frontmatter_module")

        for role in manifest.get("roles") or []:
            platform_file = (role.get("platform_files") or {}).get("claude-code")
            expected_name = ((role.get("platform_subagent_names") or {}).get("claude-code") or "").strip()
            self.assertTrue(platform_file)
            self.assertTrue(expected_name)

            path = DEBUGGER_ROOT / "platforms" / "claude-code" / ".claude" / "agents" / platform_file
            self.assertEqual(validator._frontmatter_string(path, "name"), expected_name)
            self.assertTrue(validator._frontmatter_string(path, "description"))

    def test_claude_code_agent_wrappers_are_bom_free(self) -> None:
        manifest = json.loads((DEBUGGER_ROOT / "common" / "config" / "role_manifest.json").read_text(encoding="utf-8-sig"))

        for role in manifest.get("roles") or []:
            platform_file = (role.get("platform_files") or {}).get("claude-code")
            path = DEBUGGER_ROOT / "platforms" / "claude-code" / ".claude" / "agents" / platform_file
            self.assertFalse(path.read_bytes().startswith(b"\xef\xbb\xbf"), path)

    def test_claude_code_agent_wrappers_use_platform_relative_shared_paths(self) -> None:
        scaffold = _load_module(DEBUGGER_ROOT / "scripts" / "sync_platform_scaffolds.py", "sync_platform_scaffolds_claude_module")
        ctx = scaffold.load_context(DEBUGGER_ROOT)
        manifest = json.loads((DEBUGGER_ROOT / "common" / "config" / "role_manifest.json").read_text(encoding="utf-8-sig"))

        for role in manifest.get("roles") or []:
            platform_file = role["platform_files"]["claude-code"]
            path = DEBUGGER_ROOT / "platforms" / "claude-code" / ".claude" / "agents" / platform_file
            text = path.read_text(encoding="utf-8")
            self.assertIn("../../AGENTS.md", text)
            self.assertIn("../../common/AGENT_CORE.md", text)
            self.assertEqual(text.split("---", 2)[2].lstrip("\r\n"), scaffold.agent_wrapper_body_text(ctx, "claude-code", role))

    def test_claude_code_specialist_tools_are_restricted(self) -> None:
        validator = _load_module(DEBUGGER_ROOT / "scripts" / "validate_debugger_repo.py", "validate_debugger_repo_tooling_module")
        path = DEBUGGER_ROOT / "platforms" / "claude-code" / ".claude" / "agents" / "02_triage_taxonomy.md"
        tools = validator._frontmatter_string(path, "tools")
        self.assertTrue(tools)
        self.assertNotIn("Agent(", tools)
        self.assertNotIn("Bash", tools)

    def test_write_scopes_match_shared_contract(self) -> None:
        validator = _load_module(DEBUGGER_ROOT / "scripts" / "validate_debugger_repo.py", "validate_debugger_repo_write_scope_module")
        findings = validator._write_scope_findings(DEBUGGER_ROOT)
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
