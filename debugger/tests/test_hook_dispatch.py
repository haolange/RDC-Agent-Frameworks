from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
DISPATCH_PATH = REPO_ROOT / "debugger" / "common" / "hooks" / "utils" / "codebuddy_hook_dispatch.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("codebuddy_hook_dispatch_module", DISPATCH_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["codebuddy_hook_dispatch_module"] = module
    spec.loader.exec_module(module)
    return module


class HookDispatchTests(unittest.TestCase):
    def test_extract_tool_output_file_from_claude_stdin_payload(self) -> None:
        module = _load_module()
        payload = json.dumps(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "common/knowledge/library/bugcards/BUG-001.yaml",
                },
            },
            ensure_ascii=False,
        )

        with mock.patch.dict(module.os.environ, {}, clear=True):
            self.assertEqual(
                module._extract_tool_output_file(payload),
                "common/knowledge/library/bugcards/BUG-001.yaml",
            )
            self.assertEqual(module._extract_tool_name(payload), "Write")

    def test_extract_tool_output_file_from_env_payload(self) -> None:
        module = _load_module()
        payload = json.dumps(
            {
                "result": {
                    "output_file": "common/knowledge/library/sessions/session-001/skeptic_signoff.yaml",
                }
            },
            ensure_ascii=False,
        )

        with mock.patch.dict(module.os.environ, {"CODEBUDDY_TOOL_INPUT": payload}, clear=True):
            self.assertEqual(
                module._extract_tool_output_file(""),
                "common/knowledge/library/sessions/session-001/skeptic_signoff.yaml",
            )

    def test_extract_tool_output_file_from_copilot_cli_payload(self) -> None:
        module = _load_module()
        payload = json.dumps(
            {
                "toolName": "edit",
                "toolArgs": json.dumps(
                    {
                        "file_path": "workspace/cases/case-001/runs/run-001/notes/pixel_forensics.md",
                    },
                    ensure_ascii=False,
                ),
            },
            ensure_ascii=False,
        )

        with mock.patch.dict(module.os.environ, {}, clear=True):
            self.assertEqual(
                module._extract_tool_output_file(payload),
                "workspace/cases/case-001/runs/run-001/notes/pixel_forensics.md",
            )
            self.assertEqual(module._extract_tool_name(payload), "edit")

    def test_write_bugcard_skips_non_target_path(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdin = io.StringIO(
                json.dumps(
                    {
                        "tool_name": "Write",
                        "tool_input": {
                            "file_path": "workspace/cases/case-001/reports/report.md",
                        },
                    },
                    ensure_ascii=False,
                )
            )
            with mock.patch("sys.stdin", stdin):
                self.assertEqual(module._cmd_write_bugcard(root), 0)


if __name__ == "__main__":
    unittest.main()
