from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "rules" / "workspace.RULES.md"


class WorkspaceRulesTest(unittest.TestCase):
    def test_existing_worktree_provenance_is_not_assumed_to_be_user_work(self):
        text = RULES.read_text(encoding="utf-8")

        self.assertIn("Do not infer that an existing non-main branch", text)
        self.assertIn("user-authored work merely because it exists", text)
        self.assertIn("provenance and ownership as `UNKNOWN`", text)
        self.assertIn("branch/HEAD, dirty state, and linked issue/PR", text)
        self.assertIn("Prefer disposable worktrees or short-lived branches", text)
        self.assertIn("remove them after verified merge", text)

    def test_github_routes_are_capability_specific(self):
        text = RULES.read_text(encoding="utf-8")

        self.assertIn("GitHub capability routing", text)
        self.assertIn("Projects V2 read", text)
        self.assertIn("GH_CONFIG_DIR=/workspace/.config/gh-write", text)
        self.assertIn("ghu_...", text)
        self.assertIn("X-OAuth-Scopes", text)
        self.assertIn("totalCount", text)
        self.assertIn("/workspace/.local/bin/gh", text)


if __name__ == "__main__":
    unittest.main()
