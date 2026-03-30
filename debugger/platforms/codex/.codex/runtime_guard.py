#!/usr/bin/env python3
"""Codex thin wrapper around the shared cross-platform harness guard."""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def _platform_root(default: Path | None = None) -> Path:
    return default.resolve() if default else Path(__file__).resolve().parents[1]


def _shared_utils_root(root: Path) -> Path:
    for candidate_root in (root, *root.parents):
        candidate = candidate_root / "common" / "hooks" / "utils"
        if candidate.is_dir() and (candidate / "harness_guard.py").is_file():
            return candidate
    raise FileNotFoundError("unable to resolve shared common/hooks/utils for Codex runtime guard")


UTILS_ROOT = _shared_utils_root(_platform_root())
if str(UTILS_ROOT) not in sys.path:
    sys.path.insert(0, str(UTILS_ROOT))

from harness_guard import (  # noqa: E402
    main as shared_main,
    run_accept_intake as shared_run_accept_intake,
    run_dispatch_readiness as shared_run_dispatch_readiness,
    run_dispatch_specialist as shared_run_dispatch_specialist,
    run_entry_gate as shared_run_entry_gate,
    run_final_audit as shared_run_final_audit,
    run_intake_gate as shared_run_intake_gate,
    run_preflight as shared_run_preflight,
    run_render_user_verdict as shared_run_render_user_verdict,
    run_runtime_topology as shared_run_runtime_topology,
    run_specialist_feedback as shared_run_specialist_feedback,
    validate_capability_token,
    write_run_audit_artifact,
)


def run_preflight(root: Path, *, case_root: Path | None = None):
    return shared_run_preflight(root, case_root=case_root)


def run_entry_gate(
    root: Path,
    case_root: Path,
    *,
    platform: str,
    entry_mode: str,
    backend: str,
    capture_paths: list[str] | None = None,
    mcp_configured: bool = False,
    remote_transport: str = "",
    single_agent_requested: bool = False,
):
    return shared_run_entry_gate(
        root,
        case_root,
        platform=platform,
        entry_mode=entry_mode,
        backend=backend,
        capture_paths=capture_paths,
        mcp_configured=mcp_configured,
        remote_transport=remote_transport,
        single_agent_requested=single_agent_requested,
    )


def run_accept_intake(
    root: Path,
    case_root: Path,
    *,
    platform: str,
    entry_mode: str,
    backend: str,
    capture_paths: list[str],
    case_id: str = "",
    run_id: str = "",
    session_id: str = "",
    mcp_configured: bool = False,
    remote_transport: str = "",
    single_agent_requested: bool = False,
    user_goal: str = "",
    symptom_summary: str = "",
):
    return shared_run_accept_intake(
        root,
        case_root,
        platform=platform,
        entry_mode=entry_mode,
        backend=backend,
        capture_paths=capture_paths,
        case_id=case_id,
        run_id=run_id,
        session_id=session_id,
        mcp_configured=mcp_configured,
        remote_transport=remote_transport,
        single_agent_requested=single_agent_requested,
        user_goal=user_goal,
        symptom_summary=symptom_summary,
    )


def run_intake_gate(root: Path, run_root: Path):
    return shared_run_intake_gate(root, run_root)


def run_runtime_topology(root: Path, run_root: Path, *, platform: str):
    return shared_run_runtime_topology(root, run_root, platform=platform)


def run_dispatch_readiness(root: Path, run_root: Path, *, platform: str):
    return shared_run_dispatch_readiness(root, run_root, platform=platform)


def run_dispatch_specialist(root: Path, run_root: Path, *, platform: str, target_agent: str, objective: str, ttl_seconds: int = 1800):
    return shared_run_dispatch_specialist(
        root,
        run_root,
        platform=platform,
        target_agent=target_agent,
        objective=objective,
        ttl_seconds=ttl_seconds,
    )


def run_specialist_feedback(root: Path, run_root: Path, *, timeout_seconds: int = 300, now_ms: int | None = None):
    return shared_run_specialist_feedback(root, run_root, timeout_seconds=timeout_seconds, now_ms=now_ms)


def run_final_audit(root: Path, run_root: Path, *, platform: str):
    return write_run_audit_artifact(root, run_root.resolve(), platform)


def run_render_user_verdict(root: Path, run_root: Path):
    return shared_run_render_user_verdict(root, run_root)


if __name__ == "__main__":
    raise SystemExit(shared_main())
