import unittest
from pathlib import Path


class CandidateSkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.skill = cls.root / "skills" / "candidates" / "using-theseus-marcopolo" / "SKILL.md"
        cls.text = cls.skill.read_text(encoding="utf-8")

    def test_minor_version_adds_project_cookbook_route(self):
        self.assertIn('version: "1.1.0"', self.text)
        self.assertIn("docs/cookbook/README.md", self.text)

    def test_project_cookbook_requires_accepted_revision(self):
        self.assertIn("accepted target revision", self.text)
        self.assertIn("candidate", self.text.lower())
        self.assertIn("must not become operational authority", self.text.lower())

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
