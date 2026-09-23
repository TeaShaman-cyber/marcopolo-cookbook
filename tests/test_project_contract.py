from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "project" / "project-contract.wl"
README = ROOT / "project" / "README.md"


class ProjectContractSourceTest(unittest.TestCase):
    def test_v8_source_has_required_project_level_contract(self):
        text = CONTRACT.read_text(encoding="utf-8")

        self.assertTrue(text.startswith("PROJECT_CONTRACT=<|"))
        self.assertIn('"Revision"->"2026-09-thin-router-v8"', text)
        self.assertIn('"Reply"->"PC_OK_V8"', text)
        self.assertIn('"CanonicalSource"', text)
        self.assertIn('"GitHubRouting"-><|', text)
        self.assertIn('"ChangeControl"-><|', text)
        self.assertIn('"IssueFirst"', text)
        self.assertIn('"ProjectOwnedPermission"', text)
        self.assertIn('"RoutinePromotion"', text)
        self.assertIn('"ExternalRepositories"', text)
        self.assertIn('"Precedence"', text)
        self.assertEqual(text.count("<|"), text.count("|>"))

    def test_project_owned_and_external_issue_authority_are_distinct(self):
        text = CONTRACT.read_text(encoding="utf-8")

        self.assertIn("Frequent narrow Issues are acceptable for traceability", text)
        self.assertIn("requiring explicit write permission", text)
        self.assertIn("does not imply external publication permission", text)

    def test_routine_project_owned_promotion_reuses_current_work_authorization(self):
        text = CONTRACT.read_text(encoding="utf-8")

        self.assertIn("no second merge approval", text)
        self.assertIn("base/currentness and exact head are verified", text)
        self.assertIn("required QA/CI/review gates pass", text)
        self.assertIn("no P0/P1/blocker remains", text)
        self.assertIn("external publication/release", text)
        self.assertIn("protected authority change", text)

    def test_project_contract_precedes_workspace_rules_for_same_concern(self):
        text = CONTRACT.read_text(encoding="utf-8")

        self.assertIn(
            "For routing, authority and permission, the Project Contract governs", text
        )
        self.assertIn(
            "Workspace RULES govern MarcoPolo runtime mechanics after route selection",
            text,
        )
        self.assertIn("BLOCK or remain UNKNOWN", text)

    def test_project_contract_fits_project_settings_limit(self):
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertLessEqual(len(text), 8000, f"project contract is {len(text)} chars")

    def test_compaction_preserves_reviewed_semantics(self):
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("Accepted Git source:", text)
        self.assertIn("versioned, reviewable, reproducible state", text)
        self.assertIn("Report unresolved same-concern conflicts", text)

    def test_project_contract_requires_qa_discovery_before_bespoke_verification(self):
        text = CONTRACT.read_text(encoding="utf-8")

        self.assertIn('"QADiscovery"', text)
        self.assertIn("discover existing deterministic repo/runtime QA routes", text)
        self.assertIn("Unavailable or uncovered verification remains UNKNOWN", text)

    def test_project_contract_stays_above_runtime_mechanics(self):
        text = CONTRACT.read_text(encoding="utf-8")

        for runtime_detail in (
            "GH_CONFIG_DIR=",
            "wrapper-gh.sh",
            "literal parent-path",
            "base64 payload",
        ):
            self.assertNotIn(runtime_detail, text)

    def test_readme_records_source_projection_boundary(self):
        text = README.read_text(encoding="utf-8")

        self.assertIn("project/project-contract.wl", text)
        self.assertIn("PROJECT_CONTRACT_PROBE", text)
        self.assertIn("PC_OK_V8", text)
        self.assertIn("Issue #31", text)


if __name__ == "__main__":
    unittest.main()
