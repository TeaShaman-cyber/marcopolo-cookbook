import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ACCEPTANCE = ROOT / "acceptance.sh"
README = ROOT / "README.md"


class SessionSearchAcceptanceContractTests(unittest.TestCase):
    def test_acceptance_script_exists_and_is_read_only_by_default(self):
        text = ACCEPTANCE.read_text(encoding="utf-8")
        self.assertIn("session_search.corpus verify", text)
        self.assertIn("session_search.search", text)
        self.assertIn("session_search.corpus rebuild", text)
        self.assertIn("--ingest", text)
        self.assertIn("READ_ONLY_DEFAULT", text)

    def test_acceptance_requires_explicit_ingest_path(self):
        text = ACCEPTANCE.read_text(encoding="utf-8")
        self.assertIn("INGEST_PATH_UNRESOLVED", text)
        self.assertIn("session_search.corpus ingest", text)

    def test_readme_documents_operational_sequence_and_fail_closed_states(self):
        text = README.read_text(encoding="utf-8")
        for token in (
            "Operational acceptance",
            "health",
            "verify",
            "session-scoped",
            "rebuild",
            "ALREADY_INGESTED",
            "CORPUS_LOCATION_UNRESOLVED",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
