from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MethodDocsTest(unittest.TestCase):
    def test_feynman_and_five_whys_are_linked_from_root_readme(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("[Feynman checkpoint](docs/methods/feynman-checkpoint.md)", readme)
        self.assertIn("[Five Whys](docs/methods/five-whys.md)", readme)

    def test_method_documents_exist_with_minimal_stop_rules(self):
        feynman = (ROOT / "docs/methods/feynman-checkpoint.md").read_text(encoding="utf-8")
        five_whys = (ROOT / "docs/methods/five-whys.md").read_text(encoding="utf-8")

        self.assertIn("# Feynman checkpoint", feynman)
        self.assertIn("What is being tested or changed?", feynman)
        self.assertIn("What does PASS not prove?", feynman)
        self.assertIn("stop and simplify", feynman.lower())

        self.assertIn("# Five Whys", five_whys)
        self.assertIn("What symptom was observed?", five_whys)
        self.assertIn("root cause", five_whys.lower())
        self.assertIn("postcondition", five_whys.lower())


if __name__ == "__main__":
    unittest.main()
