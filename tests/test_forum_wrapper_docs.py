from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ForumWrapperDocsTest(unittest.TestCase):
    def test_forum_notes_document_transport_and_verification_rationale(self):
        readme = (ROOT / "jester-forum/README.md").read_text(encoding="utf-8")
        required = [
            "Why this wrapper exists",
            "public read-only MCP",
            "authenticated citizen",
            "lossless inbox",
            "independent readback",
            "untrusted input",
            "mcporter",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, readme)

    def test_chatgpt_mcp_documentation_drift_receipt_is_linked_and_bounded(self):
        readme = (ROOT / "jester-forum/README.md").read_text(encoding="utf-8")
        receipt_path = ROOT / "docs/evidence/2026-09-16-get-posting-board-chatgpt-mcp-drift.md"
        self.assertTrue(receipt_path.exists())
        receipt = receipt_path.read_text(encoding="utf-8")

        self.assertIn("documentation drift", receipt.lower())
        self.assertIn("Plus", receipt)
        self.assertIn("Pro", receipt)
        self.assertIn("Business", receipt)
        self.assertIn("Enterprise/Edu", receipt)
        self.assertIn("web only", receipt.lower())
        self.assertIn("https://getpostingboard.dev/chatgpt.md", receipt)
        self.assertIn("https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt", receipt)
        self.assertIn("observation", receipt.lower())
        self.assertIn("not a permanent product guarantee", receipt.lower())
        self.assertIn("[ChatGPT MCP documentation drift receipt]", readme)

    def test_get_posting_board_probe_is_recorded_without_claiming_write_access(self):
        readme = (ROOT / "jester-forum/README.md").read_text(encoding="utf-8")
        self.assertIn("Get Posting Board", readme)
        self.assertIn("https://getpostingboard.dev/mcp", readme)
        self.assertIn("board:read board:write", readme)
        self.assertIn("401", readme)
        self.assertIn("write path is not yet configured", readme.lower())


    def test_direct_chatgpt_resolution_and_marcopolo_callback_blocker_are_recorded(self):
        readme = (ROOT / "jester-forum/README.md").read_text(encoding="utf-8")
        receipt = (ROOT / "docs/evidence/2026-09-16-get-posting-board-chatgpt-mcp-drift.md").read_text(encoding="utf-8")

        self.assertIn("jester-sonar", receipt)
        self.assertIn("new conversation", receipt.lower())
        self.assertIn("FORBIDDEN", receipt)
        self.assertIn("read access", receipt.lower())
        self.assertIn("AUTH_CALLBACK_RELAY_UNAVAILABLE", readme)
        self.assertIn("get-posting-board-auth-probe.sh", readme)
        self.assertIn("issue #34", readme.lower())
        self.assertIn("restricted to developer MCPs", receipt)
        self.assertIn("GitHub", receipt)
        self.assertIn("coexistence", receipt.lower())
        self.assertIn("multiple apps", receipt.lower())
        self.assertIn("native integrations", readme.lower())


if __name__ == "__main__":
    unittest.main()
