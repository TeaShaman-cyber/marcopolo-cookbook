from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "README-github-wrapper.md"
RULES = ROOT / "rules" / "workspace.RULES.md"
README = ROOT / "README.md"


class GitHubWriteOAuthRecoveryDocsTests(unittest.TestCase):
    def test_headless_recovery_uses_cron_helper_not_detached_nohup(self):
        text = WRAPPER.read_text(encoding="utf-8")
        start = text.index("## Expanding GitHub OAuth scopes in headless MarcoPolo")
        end = text.index("## GitHub Wiki bootstrap", start)
        section = text[start:end]
        self.assertIn("github-write-oauth-recover.sh", section)
        self.assertIn("--schedule-login", section)
        self.assertIn("--status", section)
        self.assertNotIn("nohup sh -c", section)
        self.assertIn("canonical scope set", section)
        self.assertIn("gh project list", section)
        self.assertIn("gh codespace list", section)
        self.assertNotIn("GH_WRITE_OAUTH_SCOPES=project,read:project", section)

    def test_runtime_rules_point_missing_profile_to_recovery_helper(self):
        text = RULES.read_text(encoding="utf-8")
        self.assertIn("github-write-oauth-recover.sh --schedule-login", text)
        self.assertIn("github-write-oauth-recover.sh --status", text)

    def test_root_readme_links_recovery_helper(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("github-write-oauth-recover.sh", text)


if __name__ == "__main__":
    unittest.main()
