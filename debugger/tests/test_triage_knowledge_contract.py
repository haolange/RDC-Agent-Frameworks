from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEBUGGER_ROOT = REPO_ROOT / "debugger"


class TriageKnowledgeContractTests(unittest.TestCase):
    def test_triage_agent_reads_bug_history_and_active_manifest(self) -> None:
        text = (DEBUGGER_ROOT / "common" / "agents" / "02_triage_taxonomy.md").read_text(encoding="utf-8-sig")
        for marker in (
            "knowledge/library/bugcards/",
            "knowledge/library/bugfull/",
            "knowledge/spec/registry/active_manifest.yaml",
            "candidate_bug_refs",
            "recommended_investigation_paths",
            "相似案例参考",
        ):
            self.assertIn(marker, text)

    def test_triage_skill_exports_direction_suggestion_fields(self) -> None:
        text = (DEBUGGER_ROOT / "common" / "skills" / "triage-taxonomy" / "SKILL.md").read_text(encoding="utf-8-sig")
        for marker in (
            "candidate_bug_refs",
            "recommended_investigation_paths",
            "BugCard/BugFull",
            "探索方向建议",
        ):
            self.assertIn(marker, text)

    def test_main_skill_requires_rdc_debugger_to_consume_triage_brief(self) -> None:
        text = (DEBUGGER_ROOT / "common" / "skills" / "rdc-debugger" / "SKILL.md").read_text(encoding="utf-8-sig")
        for marker in (
            "candidate_bug_refs",
            "recommended_sop",
            "recommended_investigation_paths",
            "仍由 `rdc-debugger` 决定",
        ):
            self.assertIn(marker, text)

    def test_curator_is_explicitly_post_run_only(self) -> None:
        agent_text = (DEBUGGER_ROOT / "common" / "agents" / "09_report_knowledge_curator.md").read_text(encoding="utf-8-sig")
        skill_text = (DEBUGGER_ROOT / "common" / "skills" / "report-knowledge-curator" / "SKILL.md").read_text(encoding="utf-8-sig")
        for text in (agent_text, skill_text):
            self.assertIn("不参与当前 run 的前置方向建议", text)
        self.assertIn("不读取 triage 的知识匹配结果来反向做 dispatch", agent_text)

    def test_role_manifest_describes_triage_as_history_matching_and_direction_suggestion(self) -> None:
        manifest = json.loads((DEBUGGER_ROOT / "common" / "config" / "role_manifest.json").read_text(encoding="utf-8-sig"))
        triage_role = next(role for role in (manifest.get("roles") or []) if role.get("agent_id") == "triage_agent")
        description = triage_role.get("description") or ""
        self.assertIn("BugCard/BugFull", description)
        self.assertIn("SOP", description)
        self.assertIn("exploration direction", description)


if __name__ == "__main__":
    unittest.main()
