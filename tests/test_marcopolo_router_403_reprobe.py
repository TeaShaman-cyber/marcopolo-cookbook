"""Issue #136: executable routing contract for a pre-execution 403."""

import unittest
from pathlib import Path


SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins/marcopolo-core-router/skills/marcopolo-core-router/SKILL.md"
)


class Route403DecisionContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.section = (
            SKILL.read_text(encoding="utf-8")
            .split("## 403 rule\n", 1)[1]
            .split("## Verification and persistence", 1)[0]
        )

    def test_preexecution_403_requires_neutral_probe_before_route_outage_claim(self):
        self.assertIn("MUST", self.section)
        self.assertIn('workspace_shell("date")', self.section)
        self.assertIn("CALL_BLOCKED", self.section)
        self.assertIn("ROUTE_HEALTH_UNKNOWN", self.section)
        self.assertIn("never declare the route UNAVAILABLE from one 403", self.section)

    def test_successful_canary_preserves_original_operation_failure_boundary(self):
        self.assertIn("ROUTE_AVAILABLE", self.section)
        self.assertIn("original command remains unverified", self.section)
        self.assertIn("smaller or normalized", self.section)
        self.assertIn("do not repeat the same failing payload", self.section)

    def test_fallback_requires_evidence_and_write_safe_readback(self):
        self.assertIn("max 2", self.section)
        self.assertIn("fallback only after", self.section)
        self.assertIn("postcondition", self.section)
        self.assertIn("Git or GitHub", self.section)
        self.assertIn("credential/profile", self.section)


if __name__ == "__main__":
    unittest.main()
