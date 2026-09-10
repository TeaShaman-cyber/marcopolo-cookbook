from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GithubGitAuthDocsTest(unittest.TestCase):
    def test_root_readme_links_default_git_auth_bootstrap(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("github-git-auth.sh", text)

    def test_workspace_rules_separate_git_helper_from_gh_command_profiles(self):
        text = (ROOT / "rules" / "workspace.RULES.md").read_text(encoding="utf-8")
        self.assertIn("github-git-auth.sh --install", text)
        self.assertIn("ordinary Git operations against `github.com`", text)
        self.assertIn("`gh` commands still use the explicit read/write profiles", text)

    def test_runbook_supersedes_manual_git_profile_export(self):
        text = (ROOT / "marcopolo" / "README.md").read_text(encoding="utf-8")
        self.assertIn("Default GitHub Git credential binding", text)
        self.assertIn("github-git-auth.sh --check", text)
        self.assertIn("plain `git fetch` / `git pull` / `git push`", text)


if __name__ == "__main__":
    unittest.main()
