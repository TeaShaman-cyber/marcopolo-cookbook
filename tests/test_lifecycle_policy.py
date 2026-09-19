from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / "docs" / "operations" / "lifecycle.md"
DEV_README = ROOT / "tools" / "dev" / "README.md"
ROOT_README = ROOT / "README.md"


class LifecyclePolicyContractTest(unittest.TestCase):
    def test_lifecycle_policy_exists_and_separates_authority_stages(self):
        self.assertTrue(LIFECYCLE.is_file())
        text = LIFECYCLE.read_text(encoding="utf-8")
        for marker in (
            "ACTIVE / PARKED / MIGRATED / SUPERSEDED / COMPLETED / HISTORICAL / UNKNOWN",
            "QA PASS != acceptance authority",
            "migration != acceptance",
            "Project state is a projection",
            "target-side migration receipt",
            "exact remote readback",
            "release / publication when applicable",
        ):
            self.assertIn(marker, text)

    def test_lifecycle_policy_defines_source_to_target_migration_order(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        migration = text.split("## Migration lifecycle", 1)[1].split(
            "## Pull-request disposition", 1
        )[0]
        markers = (
            "target owner",
            "target-side migration receipt",
            "preserve unresolved debt",
            "Project transfer",
            "source disposition",
            "exact remote readback",
        )
        positions = [migration.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))

    def test_dev_check_is_documented_as_first_local_gate_with_bounded_claim(self):
        text = DEV_README.read_text(encoding="utf-8")
        for marker in (
            "canonical first local QA gate",
            "exact revision",
            "QA PASS does not authorize",
            "network/runtime witnesses",
            "Project metadata",
        ):
            self.assertIn(marker, text)

    def test_root_readme_links_lifecycle_policy_and_canonical_qa(self):
        text = ROOT_README.read_text(encoding="utf-8")
        self.assertIn("docs/operations/lifecycle.md", text)
        self.assertIn("tools/dev/check", text)


if __name__ == "__main__":
    unittest.main()
