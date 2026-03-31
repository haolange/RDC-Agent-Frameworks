from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(f"PyYAML is required for tests: {exc}")


REPO_ROOT = Path(__file__).resolve().parents[2]
DEBUGGER_ROOT = REPO_ROOT / "debugger"
HARNESS_PATH = DEBUGGER_ROOT / "common" / "hooks" / "utils" / "harness_guard.py"


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _prepare_root() -> Path:
    root = Path(tempfile.mkdtemp()) / "debugger"
    shutil.copytree(DEBUGGER_ROOT / "common", root / "common")
    return root


def _seed_capture(root: Path, name: str) -> Path:
    path = root / "incoming" / name
    _write(path, f"fixture:{name}")
    return path


class HarnessGuardTests(unittest.TestCase):
    def _load_guard(self):
        return _load_module(HARNESS_PATH, f"harness_guard_{id(self)}")

    def test_accept_intake_blocks_missing_capture_and_keeps_run_uninitialized(self) -> None:
        root = _prepare_root()
        self.addCleanup(shutil.rmtree, root.parent, ignore_errors=True)
        guard = self._load_guard()
        case_root = root / "workspace" / "cases" / "case_001"

        payload = guard.run_accept_intake(
            root,
            case_root,
            platform="codex",
            entry_mode="cli",
            backend="local",
            capture_paths=[],
        )

        self.assertEqual(payload["status"], "blocked")
        self.assertFalse((case_root / "runs").is_dir())

    def test_accept_intake_writes_minimal_run_artifacts(self) -> None:
        root = _prepare_root()
        self.addCleanup(shutil.rmtree, root.parent, ignore_errors=True)
        guard = self._load_guard()
        case_root = root / "workspace" / "cases" / "case_001"
        capture_a = _seed_capture(root, "broken.rdc")
        capture_b = _seed_capture(root, "baseline.rdc")

        payload = guard.run_accept_intake(
            root,
            case_root,
            platform="codex",
            entry_mode="cli",
            backend="local",
            capture_paths=[str(capture_a), str(capture_b)],
            user_goal="debug fixture",
            symptom_summary="hair flicker",
        )

        run_root = case_root / "runs" / "run_001"
        self.assertEqual(payload["status"], "passed")
        self.assertTrue((case_root / "case.yaml").is_file())
        self.assertTrue((case_root / "case_input.yaml").is_file())
        self.assertTrue((case_root / "inputs" / "captures" / "manifest.yaml").is_file())
        self.assertTrue((case_root / "inputs" / "references" / "manifest.yaml").is_file())
        self.assertTrue((run_root / "run.yaml").is_file())
        self.assertTrue((run_root / "capture_refs.yaml").is_file())
        self.assertTrue((run_root / "notes" / "hypothesis_board.yaml").is_file())
        self.assertTrue((run_root / "artifacts" / "intake_gate.yaml").is_file())
        self.assertTrue((run_root / "artifacts" / "runtime_topology.yaml").is_file())
        intake_gate = yaml.safe_load((run_root / "artifacts" / "intake_gate.yaml").read_text(encoding="utf-8"))
        runtime_topology = yaml.safe_load((run_root / "artifacts" / "runtime_topology.yaml").read_text(encoding="utf-8"))
        self.assertEqual(intake_gate["status"], "passed")
        self.assertEqual(runtime_topology["status"], "passed")

    def test_dispatch_specialist_issues_capability_token(self) -> None:
        root = _prepare_root()
        self.addCleanup(shutil.rmtree, root.parent, ignore_errors=True)
        guard = self._load_guard()
        case_root = root / "workspace" / "cases" / "case_001"
        capture_a = _seed_capture(root, "broken.rdc")
        capture_b = _seed_capture(root, "baseline.rdc")
        guard.run_accept_intake(
            root,
            case_root,
            platform="codex",
            entry_mode="cli",
            backend="local",
            capture_paths=[str(capture_a), str(capture_b)],
        )
        run_root = case_root / "runs" / "run_001"

        payload = guard.run_dispatch_specialist(
            root,
            run_root,
            platform="codex",
            target_agent="pixel_forensics_agent",
            objective="inspect hotspot",
        )

        self.assertEqual(payload["status"], "passed")
        token = payload["capability_token"]
        self.assertTrue(Path(token["path"]).is_file())
        validation = guard.validate_capability_token(
            run_root,
            token_ref=token["path"],
            agent_id="pixel_forensics_agent",
            runtime_owner="pixel_forensics_agent",
            action="live_investigation",
            target_path=str(run_root / "notes" / "pixel_forensics.md"),
        )
        self.assertEqual(validation["status"], "passed")
        action_chain_path = root / "common" / "knowledge" / "library" / "sessions" / "sess_case-001_run-001" / "action_chain.jsonl"
        if not action_chain_path.is_file():
            action_chain_path = root / "common" / "knowledge" / "library" / "sessions" / "sess_case_001_run_001" / "action_chain.jsonl"
        events = [
            json.loads(line)
            for line in action_chain_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertTrue(any(event.get("event_type") == "dispatch" for event in events))

    def test_capability_token_rejects_wrong_agent_and_expired_token(self) -> None:
        root = _prepare_root()
        self.addCleanup(shutil.rmtree, root.parent, ignore_errors=True)
        guard = self._load_guard()
        run_root = root / "workspace" / "cases" / "case_001" / "runs" / "run_001"
        run_root.mkdir(parents=True, exist_ok=True)
        _write(run_root / "run.yaml", yaml.safe_dump({"run_id": "run_001"}, sort_keys=False))
        token = guard.issue_capability_token(
            run_root,
            target_agent="pixel_forensics_agent",
            runtime_owner="pixel_forensics_agent",
            allowed_actions=["write_note"],
            allowed_paths=[str(run_root / "notes" / "pixel_forensics.md")],
            ttl_seconds=60,
        )

        wrong_agent = guard.validate_capability_token(
            run_root,
            token_ref=token["path"],
            agent_id="shader_ir_agent",
            runtime_owner="pixel_forensics_agent",
            action="write_note",
            target_path=str(run_root / "notes" / "pixel_forensics.md"),
        )
        self.assertEqual(wrong_agent["blocking_code"], "BLOCKED_CAPABILITY_TOKEN_AGENT_MISMATCH")

        expired = guard.validate_capability_token(
            run_root,
            token_ref=token["path"],
            agent_id="pixel_forensics_agent",
            runtime_owner="pixel_forensics_agent",
            action="write_note",
            target_path=str(run_root / "notes" / "pixel_forensics.md"),
            now=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.assertEqual(expired["blocking_code"], "BLOCKED_CAPABILITY_TOKEN_EXPIRED")

    def test_render_user_verdict_requires_passed_run_compliance(self) -> None:
        root = _prepare_root()
        self.addCleanup(shutil.rmtree, root.parent, ignore_errors=True)
        guard = self._load_guard()
        run_root = root / "workspace" / "cases" / "case_001" / "runs" / "run_001"
        run_root.mkdir(parents=True, exist_ok=True)

        blocked = guard.run_render_user_verdict(root, run_root)
        self.assertEqual(blocked["status"], "blocked")
        self.assertIn("BLOCKED_RUN_COMPLIANCE_REQUIRED", blocked["blocking_codes"])

        _write(
            run_root / "artifacts" / "run_compliance.yaml",
            yaml.safe_dump({"status": "passed", "checks": []}, sort_keys=False, allow_unicode=True),
        )
        _write(
            run_root / "artifacts" / "fix_verification.yaml",
            yaml.safe_dump(
                {
                    "verdict": "root_cause_validated_fix_verified",
                    "overall_result": {"status": "passed", "verdict": "root_cause_validated_fix_verified"},
                },
                sort_keys=False,
                allow_unicode=True,
            ),
        )
        _write(run_root / "reports" / "report.md", "# report\n")
        _write(run_root / "reports" / "visual_report.html", "<html></html>\n")
        _write(run_root / "run.yaml", yaml.safe_dump({"run_id": "run_001", "session_id": "sess_fixture_001"}, sort_keys=False))
        (root / "common" / "knowledge" / "library" / "sessions").mkdir(parents=True, exist_ok=True)
        _write(root / "common" / "knowledge" / "library" / "sessions" / ".current_session", "sess_fixture_001\n")

        payload = guard.run_render_user_verdict(root, run_root)

        self.assertEqual(payload["status"], "passed")
        self.assertIn("root_cause_validated_fix_verified", payload["response_lines"][2])


    def test_dispatch_specialist_emits_runtime_lock(self) -> None:
        root = _prepare_root()
        self.addCleanup(shutil.rmtree, root.parent, ignore_errors=True)
        guard = self._load_guard()
        case_root = root / "workspace" / "cases" / "case_001"
        capture_a = _seed_capture(root, "broken.rdc")
        capture_b = _seed_capture(root, "baseline.rdc")
        guard.run_accept_intake(root, case_root, platform="codex", entry_mode="cli", backend="local", capture_paths=[str(capture_a), str(capture_b)])
        run_root = case_root / "runs" / "run_001"
        payload = guard.run_dispatch_specialist(root, run_root, platform="codex", target_agent="pixel_forensics_agent", objective="inspect hotspot")
        self.assertEqual(payload["status"], "passed")
        runtime_lock = payload["runtime_lock"]
        self.assertTrue(Path(runtime_lock["path"]).is_file())
        validation = guard.validate_runtime_lock(
            run_root,
            lock_ref=runtime_lock["path"],
            agent_id="pixel_forensics_agent",
            workflow_stage="waiting_for_specialist_brief",
            context_binding_id=runtime_lock["context_binding_id"],
            context_id=runtime_lock["context_id"],
            runtime_owner="pixel_forensics_agent",
            tool_class="live_investigation",
            output_path=str(run_root / "notes" / "pixel_forensics.md"),
        )
        self.assertEqual(validation["status"], "passed")

    def test_freeze_state_blocks_dispatch_and_user_verdict(self) -> None:
        root = _prepare_root()
        self.addCleanup(shutil.rmtree, root.parent, ignore_errors=True)
        guard = self._load_guard()
        case_root = root / "workspace" / "cases" / "case_001"
        capture_a = _seed_capture(root, "broken.rdc")
        capture_b = _seed_capture(root, "baseline.rdc")
        guard.run_accept_intake(root, case_root, platform="codex", entry_mode="cli", backend="local", capture_paths=[str(capture_a), str(capture_b)])
        run_root = case_root / "runs" / "run_001"
        guard.freeze_run(run_root, blocking_codes=["PROCESS_DEVIATION_MAIN_AGENT_OVERREACH"], reason="orchestrator overreach")
        dispatch = guard.run_dispatch_readiness(root, run_root, platform="codex")
        self.assertEqual(dispatch["status"], "blocked")
        self.assertIn("BLOCKED_FREEZE_STATE_ACTIVE", dispatch["blocking_codes"])
        verdict = guard.run_render_user_verdict(root, run_root)
        self.assertEqual(verdict["status"], "blocked")
        self.assertIn("BLOCKED_FREEZE_STATE_ACTIVE", verdict["blocking_codes"])

    def test_specialist_feedback_releases_runtime_lock_and_freezes_on_timeout(self) -> None:
        root = _prepare_root()
        self.addCleanup(shutil.rmtree, root.parent, ignore_errors=True)
        guard = self._load_guard()
        case_root = root / "workspace" / "cases" / "case_001"
        capture_a = _seed_capture(root, "broken.rdc")
        capture_b = _seed_capture(root, "baseline.rdc")
        guard.run_accept_intake(root, case_root, platform="codex", entry_mode="cli", backend="local", capture_paths=[str(capture_a), str(capture_b)])
        run_root = case_root / "runs" / "run_001"
        dispatch = guard.run_dispatch_specialist(root, run_root, platform="codex", target_agent="pixel_forensics_agent", objective="inspect hotspot")
        lock_path = Path(dispatch["runtime_lock"]["path"])
        action_chain_path = root / "common" / "knowledge" / "library" / "sessions" / "sess_case-001_run-001" / "action_chain.jsonl"
        if not action_chain_path.is_file():
            action_chain_path = root / "common" / "knowledge" / "library" / "sessions" / "sess_case_001_run_001" / "action_chain.jsonl"
        events = [json.loads(line) for line in action_chain_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        dispatch_ts = max(int(event.get("ts_ms") or 0) for event in events if event.get("event_type") == "dispatch")
        with action_chain_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({
                "schema_version": 1,
                "event_id": "evt-feedback-1",
                "ts_ms": dispatch_ts + 1,
                "run_id": "run_001",
                "session_id": "sess_case_001_run_001",
                "agent_id": "pixel_forensics_agent",
                "event_type": "artifact_write",
                "status": "ok",
                "duration_ms": 0,
                "refs": [],
                "payload": {"path": str(run_root / "notes" / "pixel_forensics.md")},
            }, ensure_ascii=False) + "\n")
        feedback = guard.run_specialist_feedback(root, run_root, now_ms=dispatch_ts + 10)
        self.assertEqual(feedback["status"], "passed")
        released = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
        self.assertEqual(released["status"], "released")
        second = guard.run_dispatch_specialist(root, run_root, platform="codex", target_agent="shader_ir_agent", objective="inspect shader")
        events = [json.loads(line) for line in action_chain_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        shader_dispatch_ts = max(
            int(event.get("ts_ms") or 0)
            for event in events
            if event.get("event_type") == "dispatch" and ((event.get("payload") or {}).get("target_agent") == "shader_ir_agent")
        )
        timed_out = guard.run_specialist_feedback(root, run_root, timeout_seconds=1, now_ms=shader_dispatch_ts + 2_000)
        self.assertEqual(timed_out["status"], "blocked")
        self.assertIn("BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT", timed_out["blocking_codes"])
        freeze_state = yaml.safe_load((run_root / "artifacts" / "freeze_state.yaml").read_text(encoding="utf-8"))
        self.assertEqual(freeze_state["status"], "frozen")
        self.assertTrue(Path(second["runtime_lock"]["path"]).is_file())

    def test_render_user_verdict_writes_finalization_receipt(self) -> None:
        root = _prepare_root()
        self.addCleanup(shutil.rmtree, root.parent, ignore_errors=True)
        guard = self._load_guard()
        run_root = root / "workspace" / "cases" / "case_001" / "runs" / "run_001"
        run_root.mkdir(parents=True, exist_ok=True)
        _write(run_root / "artifacts" / "run_compliance.yaml", yaml.safe_dump({"status": "passed", "checks": []}, sort_keys=False, allow_unicode=True))
        _write(run_root / "artifacts" / "fix_verification.yaml", yaml.safe_dump({"verdict": "root_cause_validated_fix_verified", "overall_result": {"status": "passed", "verdict": "root_cause_validated_fix_verified"}}, sort_keys=False, allow_unicode=True))
        _write(run_root / "reports" / "report.md", "# report\n")
        _write(run_root / "reports" / "visual_report.html", "<html></html>\n")
        _write(run_root / "run.yaml", yaml.safe_dump({"run_id": "run_001", "session_id": "sess_fixture_001"}, sort_keys=False))
        (root / "common" / "knowledge" / "library" / "sessions").mkdir(parents=True, exist_ok=True)
        _write(root / "common" / "knowledge" / "library" / "sessions" / ".current_session", "sess_fixture_001\n")
        payload = guard.run_render_user_verdict(root, run_root)
        self.assertEqual(payload["status"], "passed")
        receipt = yaml.safe_load((run_root / "artifacts" / "finalization_receipt.yaml").read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "issued")
        self.assertIn("finalization_receipt", payload["paths"])


if __name__ == "__main__":
    unittest.main()
