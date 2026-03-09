from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(f"PyYAML is required for tests: {exc}")


REPO_ROOT = Path(__file__).resolve().parents[2]
DEBUGGER_ROOT = REPO_ROOT / "debugger"
AUDIT_SCRIPT = DEBUGGER_ROOT / "common" / "hooks" / "utils" / "run_compliance_audit.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_base(root: Path) -> None:
    for rel in (
        Path("common/config/framework_compliance.json"),
        Path("common/config/platform_capabilities.json"),
    ):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DEBUGGER_ROOT / rel, target)


def _seed_common_session(root: Path, session_id: str, *, counterfactual: bool = True, skeptic_signed: bool = True, with_action_chain: bool = True) -> None:
    sessions_root = root / "common" / "knowledge" / "library" / "sessions"
    sessions_root.mkdir(parents=True, exist_ok=True)
    _write(sessions_root / ".current_session", f"{session_id}\n")
    evidence = {
        "session_id": session_id,
        "causal_anchor": {
            "type": "root_drawcall",
            "ref": "event:523",
            "established_by": "pixel_forensics_agent",
            "justification": "fixture anchor",
        },
        "evidence": [
            {
                "evidence_id": "anchor-1",
                "type": "causal_anchor_evidence",
                "result": "passed",
                "anchor_ref": "event:523",
                "source_tool": "rd.debug.pixel_history",
            }
        ],
    }
    if counterfactual:
        evidence["evidence"].append(
            {
                "evidence_id": "cf-1",
                "type": "counterfactual_test",
                "result": "passed",
                "description": "precision patch restored output",
            }
        )
    _write(sessions_root / session_id / "session_evidence.yaml", yaml.safe_dump(evidence, sort_keys=False, allow_unicode=True))

    signoff = [
        {
            "message_type": "SKEPTIC_SIGN_OFF",
            "from": "skeptic_agent",
            "to": "team_lead",
            "target_hypothesis": "H-001",
            "blade_review": [
                {"blade": "相关性刀", "result": "pass", "note": "ok"},
                {"blade": "覆盖性刀", "result": "pass", "note": "ok"},
                {"blade": "反事实刀", "result": "pass", "note": "ok"},
                {"blade": "工具证据刀", "result": "pass", "note": "ok"},
                {"blade": "替代假设刀", "result": "pass", "note": "ok"},
            ],
            "sign_off": {
                "signed": skeptic_signed,
                "declaration": "evidence chain is sufficient",
            },
        }
    ]
    _write(sessions_root / session_id / "skeptic_signoff.yaml", yaml.safe_dump(signoff, sort_keys=False, allow_unicode=True))

    if with_action_chain:
        lines = [
            '{"timestamp":"2026-03-09T10:00:00Z","agent":"team_lead","action_type":"message_send","message_type":"TASK_DISPATCH","message_to":"triage_agent","output_summary":"dispatch triage"}',
            '{"timestamp":"2026-03-09T10:01:00Z","agent":"capture_repro_agent","action_type":"tool_call","tool":"rd.capture.open_file","params":{"session_id":"sess-fixture","capture_file_id":"capf_fixture"},"output_summary":"capture opened"}',
            '{"timestamp":"2026-03-09T10:02:00Z","agent":"shader_ir_agent","action_type":"tool_call","tool":"rd.shader.get_source","params":{"session_id":"sess-fixture","event_id":523},"output_summary":"event 523 analyzed"}',
            '{"timestamp":"2026-03-09T10:03:00Z","agent":"skeptic_agent","action_type":"message_send","message_type":"SKEPTIC_SIGN_OFF","message_to":"team_lead","output_summary":"signed off"}',
            '{"timestamp":"2026-03-09T10:04:00Z","agent":"curator_agent","action_type":"artifact_write","params":{"path":"common/knowledge/library/sessions/' + session_id + '/session_evidence.yaml"},"output_summary":"session evidence written"}',
        ]
        _write(sessions_root / session_id / "action_chain.jsonl", "\n".join(lines) + "\n")


def _seed_run(root: Path, case_id: str, run_id: str, platform: str, coordination_mode: str, *, include_case=True, include_run=True, include_hypothesis=True, report_bug_ref=True) -> Path:
    case_root = root / "workspace" / "cases" / case_id
    run_root = case_root / "runs" / run_id
    if include_case:
        _write(case_root / "case.yaml", f"case_id: {case_id}\ncurrent_run: {run_id}\n")
    if include_run:
        _write(
            run_root / "run.yaml",
            yaml.safe_dump(
                {
                    "case_id": case_id,
                    "run_id": run_id,
                    "platform": platform,
                    "coordination_mode": coordination_mode,
                    "session_id": "sess_fixture_001",
                    "capture_file_id": "capf_fixture_001",
                },
                sort_keys=False,
                allow_unicode=True,
            ),
        )
    if include_hypothesis:
        _write(run_root / "notes" / "hypothesis_board.yaml", "hypothesis_board:\n  hypotheses: []\n")
    title_line = "BUG-PREC-FIXTURE" if report_bug_ref else "draft brief"
    _write(
        run_root / "reports" / "report.md",
        "\n".join(
            [
                f"# {title_line}",
                "",
                "session_id = sess_fixture_001",
                "capture_file_id = capf_fixture_001",
                "event 523",
                "DEBUGGER_FINAL_VERDICT",
            ],
        )
        + "\n",
    )
    _write(
        run_root / "reports" / "visual_report.html",
        "<html><body><p>session_id = sess_fixture_001</p><p>event 523</p></body></html>\n",
    )
    return run_root


def _run_audit(root: Path, platform: str, run_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--root", str(root), "--platform", platform, "--run-root", str(run_root), "--strict"],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


class RunComplianceAuditTests(unittest.TestCase):
    def _temp_root(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def test_full_capability_run_passes(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001")
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "passed")

    def test_audit_only_platform_passes_and_writes_artifact(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001")
        run_root = _seed_run(root, "case_001", "run_01", "codex", "concurrent_team")

        proc = _run_audit(root, "codex", run_root)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "passed")

    def test_brief_then_report_without_required_artifacts_fails(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        run_root = _seed_run(root, "case_001", "run_01", "copilot-ide", "staged_handoff", include_case=False, include_run=False, include_hypothesis=False, report_bug_ref=False)

        proc = _run_audit(root, "copilot-ide", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "failed")

    def test_workflow_platform_rejects_concurrent_team_shape(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001")
        run_root = _seed_run(root, "case_001", "run_01", "manus", "concurrent_team")

        proc = _run_audit(root, "manus", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "failed")

    def test_missing_session_artifacts_fail(self) -> None:
        root = self._temp_root()
        _seed_base(root)
        _seed_common_session(root, "sess_fixture_001", with_action_chain=False)
        session_root = root / "common" / "knowledge" / "library" / "sessions" / "sess_fixture_001"
        (session_root / "session_evidence.yaml").unlink()
        run_root = _seed_run(root, "case_001", "run_01", "code-buddy", "concurrent_team")

        proc = _run_audit(root, "code-buddy", run_root)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        artifact = yaml.safe_load((run_root / "artifacts" / "run_compliance.yaml").read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "failed")


if __name__ == "__main__":
    unittest.main()
