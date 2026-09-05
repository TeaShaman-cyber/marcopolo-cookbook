import unittest
from pathlib import Path


class CandidateSkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.skill = cls.root / "skills" / "candidates" / "using-theseus-marcopolo" / "SKILL.md"
        cls.text = cls.skill.read_text(encoding="utf-8")

    def test_patch_version_closes_router_authority_holes(self):
        self.assertIn('version: "1.1.1"', self.text)
        self.assertIn("docs/cookbook/README.md", self.text)

    def test_project_cookbook_provenance_is_independent_of_work_target(self):
        lower = self.text.lower()
        self.assertIn("accepted cookbook source revision", lower)
        self.assertIn("must not be inferred from the revision under operation", lower)
        self.assertIn("candidate", lower)
        self.assertIn("must not become operational authority", lower)

    def test_repository_policy_precedes_cookbook_guidance(self):
        lower = self.text.lower()
        self.assertIn("explicit user constraints", lower)
        self.assertIn("repository policy", lower)
        self.assertIn("procedural guidance", lower)
        self.assertIn("subordinate", lower)

    def test_missing_project_cookbook_is_not_auto_created(self):
        self.assertIn("do not create a project cookbook automatically", self.text.lower())
        self.assertIn("explicit user approval", self.text.lower())

    def test_runtime_and_project_guidance_compose_by_concern(self):
        self.assertIn("compose by concern", self.text.lower())
        self.assertIn("BLOCKED", self.text)
        self.assertIn("runtime cookbook", self.text.lower())
        self.assertIn("project cookbook", self.text.lower())


if __name__ == "__main__":
    unittest.main()
