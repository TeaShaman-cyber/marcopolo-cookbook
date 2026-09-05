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
        self.assertEqual(case["expected"]["event_ids"], ["evt-001", "evt-002"])
        self.assertEqual(
            case["expected"]["next_cursor"],
            encode_cursor("2026-09-06T02:00:00Z", "evt-002"),
        )

    def test_page_two_resumes_strictly_after_cursor(self):
        page1 = self.fixture["cases"]["scope_alpha_page_1"]
        page2 = self.fixture["cases"]["scope_alpha_page_2"]
        self.assertEqual(page2["request"]["cursor"], page1["expected"]["next_cursor"])
        self.assertEqual(page2["expected"]["event_ids"], ["evt-003"])
        self.assertIsNone(page2["expected"]["next_cursor"])

    def test_lifecycle_filter_is_fixture_exact(self):
        case = self.fixture["cases"]["scope_alpha_observed_only"]
        self.assertEqual(case["request"]["filters"]["lifecycle"], ["OBSERVED"])
        self.assertEqual(case["expected"]["event_ids"], ["evt-001", "evt-002"])

    def test_scope_is_exact(self):
        case = self.fixture["cases"]["scope_beta"]
        self.assertEqual(case["expected"]["event_ids"], ["evt-004"])


if __name__ == "__main__":
    unittest.main()
