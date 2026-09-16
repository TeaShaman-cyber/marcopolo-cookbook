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

    def test_get_posting_board_probe_is_recorded_without_claiming_write_access(self):
        readme = (ROOT / "jester-forum/README.md").read_text(encoding="utf-8")
        self.assertIn("Get Posting Board", readme)
        self.assertIn("https://getpostingboard.dev/mcp", readme)
        self.assertIn("board:read board:write", readme)
        self.assertIn("401", readme)
        self.assertIn("write path is not yet configured", readme.lower())


if __name__ == "__main__":
    unittest.main()
