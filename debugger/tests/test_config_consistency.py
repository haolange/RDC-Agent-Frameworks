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

        compliance_entry = (compliance.get("entry_model") or {})
        self.assertEqual(compliance_entry.get("public_entry_skill"), "rdc-debugger")
        self.assertEqual(compliance_entry.get("orchestration_role"), "team_lead")

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
        expected = module._expected_rendered_model(DEBUGGER_ROOT, "cursor", "team_lead")
        self.assertIsNotNone(expected)
        path, model = expected
        self.assertEqual(path, DEBUGGER_ROOT / "platforms" / "cursor" / "agents" / "01_team_lead.md")
        self.assertEqual(model, "opus-4.6")

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
            {"code-buddy", "claude-code", "copilot-cli", "copilot-ide", "codex", "cursor"},
        )
        self.assertEqual(mcp_only, {"claude-desktop", "manus"})

        for key in cli_first:
            self.assertEqual(platforms[key].get("allowed_entry_modes"), ["cli", "mcp"])

        for key in ("claude-desktop", "manus"):
            self.assertIn("mcp", (compliance.get("platforms") or {}).get(key, {}).get("required_surfaces") or [])


if __name__ == "__main__":
    unittest.main()
