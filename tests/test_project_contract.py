from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "project" / "project-contract.wl"
README = ROOT / "project" / "README.md"


class ProjectContractSourceTest(unittest.TestCase):
    def test_v7_source_has_required_project_level_contract(self):
        text = CONTRACT.read_text(encoding="utf-8")

        self.assertTrue(text.startswith("PROJECT_CONTRACT=<|"))
        self.assertIn('"Revision"->"2026-09-thin-router-v7"', text)
        self.assertIn('"Reply"->"PC_OK_V7"', text)
        self.assertIn('"CanonicalSource"', text)
        self.assertIn('"GitHubRouting"-><|', text)
        self.assertIn('"ChangeControl"-><|', text)
        self.assertIn('"IssueFirst"', text)
        self.assertIn('"BoundedPermission"', text)
        self.assertEqual(text.count("<|"), text.count("|>"))

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
        self.assertIn("PC_OK_V7", text)
        self.assertIn("Issue #31", text)


if __name__ == "__main__":
    unittest.main()
