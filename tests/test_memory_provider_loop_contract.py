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

    def test_relationships_are_scope_bound_and_fail_closed(self):
        for marker in (
            "relation.scope",
            "RELATION_SCOPE_MISMATCH",
            "INTEGRITY_SCOPE_VIOLATION",
            "must not expose unauthorized endpoint IDs",
        ):
            self.assertIn(marker, self.text)

    def test_scope_is_authorized_from_trusted_execution_context(self):
        for marker in (
            "trusted_principal_id",
            "allowed_scopes",
            "AUTHZ_SCOPE_DENIED",
            "before any backend query",
        ):
            self.assertIn(marker, self.text)

    def test_managed_postgres_is_first_class_backend_lane(self):
        for marker in (
            "Managed PostgreSQL",
            "authoritative mutable store candidate",
            "local embedded backends",
            "not an architectural dependency on Neon",
        ):
            self.assertIn(marker, self.text)

    def test_retain_replays_immutable_receipt(self):
        for marker in (
            "immutable receipt",
            "attempt-local diagnostic",
            "same stored receipt",
        ):
            self.assertIn(marker, self.text)

    def test_operation_id_is_bound_to_request_fingerprint(self):
        for marker in (
            "request_fingerprint",
            "IDEMPOTENCY_KEY_REUSE_MISMATCH",
            "same operation_id with different canonical bytes",
        ):
            self.assertIn(marker, self.text)

    def test_portable_core_has_versioned_exact_semantics(self):
        for marker in (
            "core_schema_version = memory-core-v0.1",
            "OBSERVED | CANDIDATE | PENDING | SUPERSEDED | TOMBSTONED",
            "created_at DESC, event_id ASC",
            "cursor = base64url(created_at, event_id)",
            "fixture-exact conformance",
        ):
            self.assertIn(marker, self.text)

if __name__ == "__main__":
    unittest.main()
