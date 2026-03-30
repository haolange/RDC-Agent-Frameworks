from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEBUGGER_ROOT = REPO_ROOT / "debugger"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class ConfigConsistencyTests(unittest.TestCase):
    def test_tool_catalog_snapshot_reflects_shader_replace_and_debug_contracts(self) -> None:
        snapshot = _read_json(DEBUGGER_ROOT / "common" / "config" / "tool_catalog.snapshot.json")
        tools = {str(item.get("name") or ""): item for item in snapshot.get("tools") or []}

        replace_tool = tools["rd.shader.edit_and_replace"]
        self.assertIn("event_id", replace_tool.get("param_names") or [])
        self.assertIn("ops", replace_tool.get("param_names") or [])
        self.assertIn("replacement_id", replace_tool.get("returns_raw") or "")
        self.assertIn("resolved_event_id", replace_tool.get("returns_raw") or "")
        self.assertIn("compile_flags", replace_tool.get("returns_raw") or "")
        self.assertIn("patch_diff", replace_tool.get("returns_raw") or "")
        self.assertIn("shader_source_mismatch", replace_tool.get("returns_raw") or "")
        self.assertNotIn("mock_applied", replace_tool.get("returns_raw") or "")

        debug_tool = tools["rd.shader.debug_start"]
        self.assertIn("resolved_context", debug_tool.get("returns_raw") or "")
        self.assertIn("resolved_event_id", debug_tool.get("returns_raw") or "")
        self.assertIn("failure_stage", debug_tool.get("returns_raw") or "")
        self.assertIn("failure_reason", debug_tool.get("returns_raw") or "")
        self.assertIn("attempts", debug_tool.get("returns_raw") or "")

        pipeline_tool = tools["rd.pipeline.get_shader"]
        self.assertIn("event_id", pipeline_tool.get("param_names") or [])
        self.assertIn("resolved_event_id", pipeline_tool.get("returns_raw") or "")

    def test_platform_keys_and_cursor_alignment(self) -> None:
        compliance = _read_json(DEBUGGER_ROOT / "common" / "config" / "framework_compliance.json")
        capabilities = _read_json(DEBUGGER_ROOT / "common" / "config" / "platform_capabilities.json")
        routing = _read_json(DEBUGGER_ROOT / "common" / "config" / "model_routing.json")
        manifest = _read_json(DEBUGGER_ROOT / "common" / "config" / "role_manifest.json")

        capability_platforms = set((capabilities.get("platforms") or {}).keys())
        compliance_platforms = set((compliance.get("platforms") or {}).keys())
        self.assertEqual(capability_platforms, compliance_platforms)
        self.assertIn("cursor", capability_platforms)

        class_members = {
            platform
            for members in (routing.get("platform_classes") or {}).values()
            for platform in members
        }
        self.assertEqual(capability_platforms, class_members)

        for profile in (routing.get("profiles") or {}).values():
            rendered = set((profile.get("platform_rendering") or {}).keys())
            self.assertEqual(capability_platforms, rendered)

        expected_role_platforms = {
            key
            for key, row in (capabilities.get("platforms") or {}).items()
            if ((row.get("capabilities") or {}).get("custom_agents") or {}).get("supported")
        }
        self.assertIn("cursor", expected_role_platforms)

        for key, row in (capabilities.get("platforms") or {}).items():
            self.assertTrue(((row.get("capabilities") or {}).get("skills") or {}).get("supported"), key)

        for role in (manifest.get("roles") or []):
            self.assertEqual(set((role.get("platform_files") or {}).keys()), expected_role_platforms)
        triage_role = next(role for role in (manifest.get("roles") or []) if role.get("agent_id") == "triage_agent")
        self.assertIn("BugCard/BugFull", triage_role.get("description") or "")
        self.assertIn("exploration direction", triage_role.get("description") or "")

        compliance_entry = (compliance.get("entry_model") or {})
        self.assertEqual(compliance_entry.get("public_entry_skill"), "rdc-debugger")
        self.assertNotIn("orchestration_role", compliance_entry)
        self.assertEqual(capabilities["platforms"]["cursor"]["coordination_mode"], "staged_handoff")
        self.assertEqual(capabilities["platforms"]["cursor"]["sub_agent_mode"], "puppet_sub_agents")
        self.assertEqual(capabilities["platforms"]["cursor"]["local_live_runtime_policy"], "multi_context_orchestrated")
        self.assertEqual(capabilities["platforms"]["codex"]["local_live_runtime_policy"], "multi_context_orchestrated")
        self.assertEqual(capabilities["platforms"]["copilot-cli"]["local_live_runtime_policy"], "multi_context_orchestrated")
        self.assertEqual(capabilities["platforms"]["copilot-ide"]["local_live_runtime_policy"], "multi_context_orchestrated")
        self.assertEqual(capabilities["platforms"]["claude-code"]["sub_agent_mode"], "team_agents")
        self.assertEqual(capabilities["platforms"]["code-buddy"]["sub_agent_mode"], "team_agents")
        self.assertEqual(capabilities["platforms"]["claude-desktop"]["specialist_dispatch_requirement"], "required")
        self.assertEqual(capabilities["platforms"]["manus"]["specialist_dispatch_requirement"], "required")
        self.assertEqual(capabilities["platforms"]["codex"]["host_delegation_policy"], "platform_managed")
        self.assertEqual(capabilities["platforms"]["codex"]["host_delegation_fallback"], "none")
        self.assertEqual(capabilities["platforms"]["manus"]["agent_description_mode"], "spawn_instruction_only")
        self.assertEqual(capabilities["platforms"]["claude-code"]["enforcement_tier"], "native-hooks")
        self.assertEqual(capabilities["platforms"]["copilot-cli"]["enforcement_tier"], "native-hooks")
        self.assertEqual(capabilities["platforms"]["cursor"]["enforcement_tier"], "pseudo-hooks")
        self.assertEqual(capabilities["platforms"]["code-buddy"]["enforcement_tier"], "pseudo-hooks")
        self.assertEqual(capabilities["platforms"]["codex"]["enforcement_tier"], "pseudo-hooks")
        self.assertEqual(capabilities["platforms"]["claude-desktop"]["enforcement_tier"], "no-hooks")
        self.assertEqual(capabilities["platforms"]["manus"]["enforcement_tier"], "no-hooks")
        self.assertFalse(capabilities["platforms"]["cursor"]["capabilities"]["hooks"]["supported"])
        self.assertFalse(capabilities["platforms"]["code-buddy"]["capabilities"]["hooks"]["supported"])
        self.assertTrue(capabilities["platforms"]["claude-code"]["capabilities"]["hooks"]["supported"])
        self.assertTrue(capabilities["platforms"]["copilot-cli"]["capabilities"]["hooks"]["supported"])
        self.assertEqual(compliance["platforms"]["cursor"]["enforcement_mode"], "pseudo_hook_harness")
        self.assertEqual(compliance["platforms"]["code-buddy"]["enforcement_mode"], "pseudo_hook_harness")
        self.assertEqual(compliance["platforms"]["claude-code"]["enforcement_mode"], "native_hook_harness")
        self.assertEqual(compliance["platforms"]["copilot-cli"]["enforcement_mode"], "native_hook_harness")
        self.assertEqual(compliance["platforms"]["claude-desktop"]["enforcement_mode"], "no_hook_audit")
        self.assertEqual(compliance["platforms"]["manus"]["enforcement_mode"], "no_hook_audit")

    def test_validate_tool_contract_ignores_known_tool_field_paths(self) -> None:
        module = _load_module(DEBUGGER_ROOT / "scripts" / "validate_tool_contract.py", "validate_tool_contract_field_path_module")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text("preview path: rd.session.get_context.preview.display\n", encoding="utf-8")
            findings = module.check_unknown_tools([path], {"rd.session.get_context"})
            self.assertEqual(findings, {})

    def test_codex_plugin_model_routing_uses_inherit_for_not_packaged_profiles(self) -> None:
        routing = _read_json(DEBUGGER_ROOT / "common" / "config" / "model_routing.json")
        capabilities = _read_json(DEBUGGER_ROOT / "common" / "config" / "platform_capabilities.json")
        self.assertEqual(((capabilities["platforms"]["codex_plugin"]["capabilities"] or {}).get("per_agent_model") or {}).get("rendered"), "not-packaged")
        for profile_name in ("orchestrator", "investigator", "verifier", "reporter"):
            self.assertEqual((routing["profiles"][profile_name]["platform_rendering"] or {}).get("codex_plugin"), "inherit")

    def test_repo_validator_accepts_pseudo_hook_surface_and_skill_files(self) -> None:
        module = _load_module(DEBUGGER_ROOT / "scripts" / "validate_debugger_repo.py", "validate_debugger_repo_surface_module")
        capabilities = _read_json(DEBUGGER_ROOT / "common" / "config" / "platform_capabilities.json")
        self.assertTrue(module._required_surface_supported(capabilities["platforms"]["code-buddy"], "hooks"))
        self.assertTrue(module._required_surface_supported(capabilities["platforms"]["cursor"], "hooks"))
        self.assertFalse(module._native_surface_supported(capabilities["platforms"]["code-buddy"], "hooks"))
        self.assertTrue(module._platform_is_inherit_only(capabilities["platforms"]["codex_plugin"]))
        self.assertEqual(capabilities["platforms"]["codex_plugin"]["agent_description_mode"], "skill_files")

    def test_validate_tool_contract_reader_reports_invalid_adapter_json(self) -> None:
        module = _load_module(DEBUGGER_ROOT / "scripts" / "validate_tool_contract.py", "validate_tool_contract_module")
        with tempfile.TemporaryDirectory() as tmp:
            bad_json = Path(tmp) / "platform_adapter.json"
            bad_json.write_text('{"paths":{"tools_source_root":"tools",}}\n', encoding="utf-8")

            with self.assertRaises(ValueError) as exc:
                module.read_json(bad_json)

            self.assertIn("invalid JSON in", str(exc.exception))
            self.assertNotIn("forward slashes or escaped backslashes", str(exc.exception))

    def test_runtime_tool_contract_reader_reports_invalid_adapter_json(self) -> None:
        module = _load_module(
            DEBUGGER_ROOT / "common" / "hooks" / "utils" / "validate_tool_contract_runtime.py",
            "validate_tool_contract_runtime_module",
        )
        with tempfile.TemporaryDirectory() as tmp:
            bad_json = Path(tmp) / "platform_adapter.json"
            bad_json.write_text('{"paths":{"tools_source_root":"tools",}}\n', encoding="utf-8")

            with self.assertRaises(ValueError) as exc:
                module._read_json(bad_json)

            self.assertIn("invalid JSON in", str(exc.exception))
            self.assertNotIn("forward slashes or escaped backslashes", str(exc.exception))

    def test_repo_validator_expected_rendered_model_supports_cursor(self) -> None:
        module = _load_module(DEBUGGER_ROOT / "scripts" / "validate_debugger_repo.py", "validate_debugger_repo_module")
        expected = module._expected_rendered_model(DEBUGGER_ROOT, "cursor", "triage_agent")
        self.assertIsNotNone(expected)
        path, model = expected
        self.assertEqual(path, DEBUGGER_ROOT / "platforms" / "cursor" / "agents" / "02_triage_taxonomy.md")
        self.assertEqual(model, "sonnet-4.6")

    def test_hypothesis_board_schema_requires_intent_gate(self) -> None:
        import yaml

        schema = yaml.safe_load(
            (DEBUGGER_ROOT / "common" / "hooks" / "schemas" / "hypothesis_board_schema.yaml").read_text(
                encoding="utf-8-sig"
            )
        )
        board = schema.get("hypothesis_board") or {}
        self.assertIn("intent_gate", board.get("required_fields") or [])
        intent_gate = board.get("intent_gate") or {}
        self.assertIn("decision", intent_gate.get("required_fields") or [])
        self.assertEqual(
            set(intent_gate.get("decision_allowed") or []),
            {"debugger", "analyst", "optimizer", "out_of_scope_or_ambiguous"},
        )

    def test_platform_adapter_required_paths_include_zero_install_runtime(self) -> None:
        adapter = _read_json(DEBUGGER_ROOT / "common" / "config" / "platform_adapter.json")
        required_paths = set(((adapter.get("validation") or {}).get("required_paths") or []))
        for rel in (
            "README.md",
            "docs/tools.md",
            "docs/session-model.md",
            "docs/agent-model.md",
            "spec/tool_catalog.json",
            "rdx.bat",
            "binaries/windows/x64/manifest.runtime.json",
            "binaries/windows/x64/python/python.exe",
        ):
            self.assertIn(rel, required_paths)
        self.assertEqual(((adapter.get("cli") or {}).get("launcher") or ""), "rdx.bat")

    def test_mcp_opt_in_configs_use_zero_install_launcher(self) -> None:
        shared = _read_json(DEBUGGER_ROOT / "common" / "config" / "mcp_servers.json")
        shared_server = (shared.get("servers") or {}).get("renderdoc-platform-mcp") or {}
        self.assertEqual(shared_server.get("command"), "cmd")
        self.assertEqual(shared_server.get("args"), ["/c", "${DEBUGGER_PLATFORM_TOOLS_ROOT}/rdx.bat", "--non-interactive", "mcp"])
        self.assertEqual(shared_server.get("cwd"), "${DEBUGGER_PLATFORM_TOOLS_ROOT}")
        self.assertNotIn("run_mcp.py", json.dumps(shared, ensure_ascii=False))

        for rel in (
            "platforms/claude-code/.claude/settings.mcp.opt-in.json",
            "platforms/claude-desktop/claude_desktop_config.opt-in.json",
            "platforms/code-buddy/.mcp.opt-in.json",
            "platforms/copilot-cli/.mcp.opt-in.json",
            "platforms/copilot-ide/.github/mcp.opt-in.json",
            "platforms/cursor/.cursor/mcp.opt-in.json",
        ):
            payload = _read_json(DEBUGGER_ROOT / rel)
            server = (payload.get("mcpServers") or {}).get("renderdoc-platform-mcp") or {}
            self.assertEqual(server.get("command"), "cmd", rel)
            self.assertEqual(server.get("args"), ["/c", "${DEBUGGER_PLATFORM_TOOLS_ROOT}/rdx.bat", "--non-interactive", "mcp"], rel)
            self.assertNotIn("run_mcp.py", json.dumps(payload, ensure_ascii=False), rel)

        codex_opt_in = (DEBUGGER_ROOT / "platforms" / "codex" / ".codex" / "config.mcp.opt-in.toml").read_text(encoding="utf-8-sig")
        self.assertIn('command = "cmd"', codex_opt_in)
        self.assertIn('args = ["/c", "${DEBUGGER_PLATFORM_TOOLS_ROOT}/rdx.bat", "--non-interactive", "mcp"]', codex_opt_in)
        self.assertNotIn('run_mcp.py', codex_opt_in)

        plugin_opt_in = (DEBUGGER_ROOT / "platforms" / "codex_plugin" / "rdc-debugger" / "references" / "mcp-opt-in.sample.toml").read_text(encoding="utf-8-sig")
        self.assertIn('command = "cmd"', plugin_opt_in)
        self.assertIn('args = ["/c", "${RDC_DEBUGGER_PLUGIN_ROOT}/tools/rdx.bat", "--non-interactive", "mcp"]', plugin_opt_in)
        self.assertNotIn('run_mcp.py', plugin_opt_in)

    def test_platform_entry_modes_are_consistent(self) -> None:
        capabilities = _read_json(DEBUGGER_ROOT / "common" / "config" / "platform_capabilities.json")
        compliance = _read_json(DEBUGGER_ROOT / "common" / "config" / "framework_compliance.json")

        platforms = capabilities.get("platforms") or {}
        cli_first = {
            key
            for key, row in platforms.items()
            if row.get("default_entry_mode") == "cli"
        }
        mcp_only = {
            key
            for key, row in platforms.items()
            if row.get("allowed_entry_modes") == ["mcp"]
        }

        self.assertEqual(
            cli_first,
            {"code-buddy", "claude-code", "copilot-cli", "copilot-ide", "codex", "codex_plugin", "cursor"},
        )
        self.assertEqual(mcp_only, {"claude-desktop", "manus"})

        for key in cli_first:
            self.assertEqual(platforms[key].get("allowed_entry_modes"), ["cli", "mcp"])

        for key in ("claude-desktop", "manus"):
            self.assertIn("mcp", (compliance.get("platforms") or {}).get(key, {}).get("required_surfaces") or [])

    def test_runtime_mode_truth_snapshot_uses_runtime_parallelism_ceiling(self) -> None:
        snapshot = _read_json(DEBUGGER_ROOT / "common" / "config" / "runtime_mode_truth.snapshot.json")
        modes = snapshot.get("modes") or {}
        self.assertEqual(modes["local_cli"]["runtime_parallelism_ceiling"], "multi_context_multi_owner")
        self.assertEqual(modes["local_mcp"]["runtime_parallelism_ceiling"], "multi_context_multi_owner")
        self.assertEqual(modes["remote_daemon"]["runtime_parallelism_ceiling"], "single_runtime_owner")
        self.assertEqual(modes["remote_mcp"]["runtime_parallelism_ceiling"], "single_runtime_owner")
        self.assertEqual(modes["remote_mcp"]["host_coordination_gate"], "frameworks_platform_matrix_applies")


if __name__ == "__main__":
    unittest.main()
