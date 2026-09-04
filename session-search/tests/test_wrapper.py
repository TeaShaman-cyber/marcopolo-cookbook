import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "search.sh"
README = ROOT / "README.md"

class SessionSearchWrapperContractTests(unittest.TestCase):
    def test_wrapper_is_corpus_first_and_restart_safe(self):
        text = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("SESSION_SEARCH_CORPUS", text)
        self.assertIn("runtime.env", text)
        self.assertIn("--corpus", text)
        self.assertNotIn("session-search-full.sqlite3", text)
        self.assertNotIn(" --db ", text)

    def test_wrapper_does_not_scan_filesystem_for_corpus(self):
        text = WRAPPER.read_text(encoding="utf-8")
        self.assertNotIn("find /workspace", text)
        self.assertNotIn("exec rg ", text)
        self.assertNotIn("exec grep ", text)

    def test_readme_documents_binding_and_reference_discovery(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("runtime.env", text)
        self.assertIn("SESSION_SEARCH_CORPUS", text)
        self.assertIn("/workspace/tools/search/search.sh", text)

if __name__ == "__main__":
    unittest.main()
