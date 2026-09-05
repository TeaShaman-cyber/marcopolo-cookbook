from pathlib import Path
import unittest

DOC = Path(__file__).resolve().parents[1] / "docs/research/memory-provider-loop-issue-17.md"

class MemoryProviderLoopContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOC.read_text(encoding="utf-8")

    def test_retain_commit(self):
        for marker in ("operation_id", "DURABLY_COMMITTED", "lost acknowledgement"):
            self.assertIn(marker, self.text)

    def test_conflict_complete_recall(self):
        for marker in ("conflict-complete recall", "same snapshot", "tombstone"):
            self.assertIn(marker, self.text)

    def test_admission_precedes_write(self):
        for marker in ("retention admission gate", "before canonical durable write", "secret canary"):
            self.assertIn(marker, self.text)

    def test_adapter_attribution(self):
        for marker in ("adapter-only canary", "adapter disabled", "direct adapter"):
            self.assertIn(marker, self.text)

    def test_core_conformance(self):
        for marker in ("Core conformance lane", "stable IDs", "deterministic ordering"):
            self.assertIn(marker, self.text)

    def test_cross_client_unknown(self):
        self.assertIn("CROSS_CLIENT_PERSISTENCE", self.text)
        self.assertIn("UNKNOWN", self.text)

    def test_managed_postgres_is_first_class_backend_lane(self):
        for marker in (
            "Managed PostgreSQL",
            "authoritative mutable store candidate",
            "local embedded backends",
            "not an architectural dependency on Neon",
        ):
            self.assertIn(marker, self.text)

if __name__ == "__main__":
    unittest.main()
