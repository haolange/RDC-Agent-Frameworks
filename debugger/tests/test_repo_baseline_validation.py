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
        validator = _load_module(DEBUGGER_ROOT / "scripts" / "validate_debugger_repo.py", "validate_debugger_repo_docs_module")
        findings = validator._doc_contract_findings(DEBUGGER_ROOT)
        self.assertEqual(findings, [])

    def test_scaffold_expected_paths_cover_cursor(self) -> None:
        scaffold = _load_module(DEBUGGER_ROOT / "scripts" / "sync_platform_scaffolds.py", "sync_platform_scaffolds_module")
        ctx = scaffold.load_context(DEBUGGER_ROOT)
        expected = scaffold.expected_files(ctx, "cursor")
        self.assertIn(DEBUGGER_ROOT / "platforms" / "cursor" / ".cursorrules", expected)
        self.assertIn(DEBUGGER_ROOT / "platforms" / "cursor" / ".cursor" / "mcp.json", expected)
        self.assertIn(DEBUGGER_ROOT / "platforms" / "cursor" / "agents" / "01_team_lead.md", expected)
        self.assertIn(DEBUGGER_ROOT / "platforms" / "cursor" / "skills" / "renderdoc-rdc-gpu-debug" / "SKILL.md", expected)
        self.assertIn(DEBUGGER_ROOT / "platforms" / "cursor" / "hooks" / "hooks.json", expected)

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

    def test_claude_code_default_agent_is_team_lead(self) -> None:
        validator = _load_module(DEBUGGER_ROOT / "scripts" / "validate_debugger_repo.py", "validate_debugger_repo_claude_agent_module")
        findings = validator._claude_code_agent_findings(DEBUGGER_ROOT)
        self.assertEqual(findings, [])

        settings = json.loads(
            (DEBUGGER_ROOT / "platforms" / "claude-code" / ".claude" / "settings.json").read_text(
                encoding="utf-8-sig"
            )
        )
        self.assertEqual(settings.get("agent"), "team-lead")

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

    def test_claude_code_team_lead_tools_are_restricted(self) -> None:
        validator = _load_module(DEBUGGER_ROOT / "scripts" / "validate_debugger_repo.py", "validate_debugger_repo_tooling_module")
        path = DEBUGGER_ROOT / "platforms" / "claude-code" / ".claude" / "agents" / "01_team_lead.md"
        tools = validator._frontmatter_string(path, "tools")
        allowlist = validator._agent_allowlist(tools)

        self.assertIn("Agent(", tools)
        self.assertNotIn("Bash", tools)
        self.assertEqual(
            allowlist,
            {
                "triage-taxonomy",
                "capture-repro",
                "pass-graph-pipeline",
                "pixel-value-forensics",
                "shader-ir",
                "driver-device",
                "skeptic",
                "report-knowledge-curator",
            },
        )

    def test_write_scopes_match_shared_contract(self) -> None:
        validator = _load_module(DEBUGGER_ROOT / "scripts" / "validate_debugger_repo.py", "validate_debugger_repo_write_scope_module")
        findings = validator._write_scope_findings(DEBUGGER_ROOT)
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
