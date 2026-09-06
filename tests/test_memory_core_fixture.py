from pathlib import Path
import base64
import json
import unittest

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "memory-core-v0.1.json"


def encode_cursor(created_at: str, event_id: str) -> str:
    raw = f"{created_at}\n{event_id}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


class MemoryCoreFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_version_and_lifecycle_vocabulary_are_exact(self):
        self.assertEqual(self.fixture["core_schema_version"], "memory-core-v0.1")
        self.assertEqual(
            self.fixture["lifecycle_vocabulary"],
            ["OBSERVED", "CANDIDATE", "PENDING", "SUPERSEDED", "TOMBSTONED"],
        )

    def test_page_one_has_normative_tie_break_and_cursor(self):
        case = self.fixture["cases"]["scope_alpha_page_1"]
        self.assertEqual(case["request"]["limit"], 2)
        self.assertEqual([item["event_id"] for item in case["expected"]["items"]], ["evt-001", "evt-002"])
        self.assertEqual(
            case["expected"]["next_cursor"],
            encode_cursor("2026-09-06T02:00:00Z", "evt-002"),
        )

    def test_page_two_resumes_strictly_after_cursor(self):
        page1 = self.fixture["cases"]["scope_alpha_page_1"]
        page2 = self.fixture["cases"]["scope_alpha_page_2"]
        self.assertEqual(page2["request"]["cursor"], page1["expected"]["next_cursor"])
        self.assertEqual([item["event_id"] for item in page2["expected"]["items"]], ["evt-003", "evt-005"])
        self.assertEqual(page2["expected"]["next_cursor"], encode_cursor("2026-09-06T00:30:00Z", "evt-005"))

    def test_lifecycle_filter_is_fixture_exact(self):
        case = self.fixture["cases"]["scope_alpha_observed_only"]
        self.assertEqual(case["request"]["filters"]["lifecycle"], ["OBSERVED"])
        self.assertEqual([item["event_id"] for item in case["expected"]["items"]], ["evt-001", "evt-005", "evt-006"])

    def test_scope_is_exact(self):
        case = self.fixture["cases"]["scope_beta"]
        self.assertEqual([item["event_id"] for item in case["expected"]["items"]], ["evt-004"])

    def test_full_packet_contains_provenance_and_safety_state(self):
        packet = self.fixture["cases"]["scope_alpha_page_1"]["expected"]
        self.assertEqual(
            set(packet),
            {"core_schema_version", "scope", "items", "conflicts", "supersession", "tombstones", "next_cursor", "result_state"},
        )
        self.assertTrue(packet["items"])
        for item in packet["items"]:
            self.assertIn("provenance", item)
            self.assertTrue(item["provenance"]["source_ref"])

    def test_out_of_cutoff_conflict_is_still_in_decision_packet(self):
        packet = self.fixture["cases"]["scope_alpha_page_1"]["expected"]
        page_ids = {item["event_id"] for item in packet["items"]}
        conflict = packet["conflicts"][0]
        self.assertIn(conflict["left_event_id"], page_ids)
        self.assertNotIn(conflict["right_event_id"], page_ids)
        self.assertEqual(conflict["relation_id"], "conflict-001")

    def test_conflict_surfaces_when_second_endpoint_is_paged(self):
        packet = self.fixture["cases"]["scope_alpha_page_2"]["expected"]
        page_ids = {item["event_id"] for item in packet["items"]}
        self.assertIn("evt-005", page_ids)
        self.assertTrue(packet["conflicts"], "page 2 must surface applicable conflicts")
        self.assertEqual(packet["conflicts"][0]["relation_id"], "conflict-001")
        self.assertEqual(packet["result_state"], "CONFLICT")

    def test_supersession_and_tombstone_are_fixture_exact(self):
        packet = self.fixture["cases"]["scope_alpha_page_1"]["expected"]
        self.assertEqual(packet["supersession"][0]["relation_id"], "supersede-001")
        self.assertEqual(packet["tombstones"][0]["relation_id"], "tombstone-001")

    def test_empty_result_is_miss_unknown(self):
        packet = self.fixture["cases"]["scope_alpha_missing_event"]["expected"]
        self.assertEqual(packet["items"], [])
        self.assertEqual(packet["result_state"], "MISS_UNKNOWN")

    def test_cross_scope_relation_vectors_fail_closed(self):
        self.assertIn("relation_policy", self.fixture)
        self.assertIn("relation_admission_cases", self.fixture)
        policy = self.fixture["relation_policy"]
        self.assertEqual(policy["scope_binding"], "same_effective_scope")
        for relations in self.fixture["relations"].values():
            for relation in relations:
                self.assertEqual(relation["scope"], "alpha")
        cases = self.fixture["relation_admission_cases"]
        for name in (
            "cross_scope_conflict",
            "cross_scope_supersession",
            "cross_scope_tombstone",
        ):
            expected = cases[name]["expected"]
            self.assertEqual(expected["error"], "RELATION_SCOPE_MISMATCH")
            self.assertFalse(expected["persisted"])
            self.assertFalse(expected["unauthorized_endpoint_metadata_exposed"])

    def test_corrupt_cross_scope_relation_fails_closed_on_recall(self):
        self.assertIn("relation_integrity_cases", self.fixture)
        expected = self.fixture["relation_integrity_cases"]["cross_scope_relation_detected"]["expected"]
        self.assertEqual(expected["error"], "INTEGRITY_SCOPE_VIOLATION")
        self.assertFalse(expected["normal_packet_returned"])
        self.assertFalse(expected["unauthorized_endpoint_metadata_exposed"])

    def test_scope_authorization_is_bound_to_trusted_principal(self):
        auth = self.fixture["authorization"]
        self.assertEqual(auth["principal_source"], "trusted_execution_context")
        self.assertEqual(auth["principals"]["principal-alpha"]["allowed_scopes"], ["alpha"])
        denied = self.fixture["auth_cases"]["principal_alpha_requests_beta"]["expected"]
        self.assertEqual(denied["error"], "AUTHZ_SCOPE_DENIED")
        self.assertFalse(denied["backend_query_permitted"])


if __name__ == "__main__":
    unittest.main()
