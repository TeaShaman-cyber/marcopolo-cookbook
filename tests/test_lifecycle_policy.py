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
            "minimum viable lifecycle policy",
            "small, reviewable batches",
            "QA PASS != acceptance authority",
            "migration != acceptance",
            "Project state is a projection",
            "target-side migration receipt",
            "exact remote readback",
            "release / publication when applicable",
            "tools/project-roadmap/check",
            "ProjectV2.items",
            "projectItems",
        ):
            self.assertIn(marker, text)

    def test_lifecycle_policy_defines_source_to_target_migration_order(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        migration = text.split("## Migration lifecycle", 1)[1].split(
            "## Pull-request disposition", 1
        )[0]
        markers = (
            "target owner",
            "preserve unresolved debt",
            "target-side migration receipt",
            "exact target-receipt readback",
            "source disposition",
            "Project synchronization",
            "exact final readback",
        )
        positions = [migration.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))

    def test_terminal_disposition_precedes_final_readback(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        normal = text.split("## Normal lifecycle", 1)[1].split(
            "## Migration lifecycle", 1
        )[0]
        self.assertLess(
            normal.index("terminal disposition"), normal.index("exact remote readback")
        )

    def test_dev_check_is_documented_as_first_local_gate_with_bounded_claim(self):
        text = DEV_README.read_text(encoding="utf-8")
        for marker in (
            "canonical first local QA gate",
            "clean worktree",
            "identity for the complete tested content",
            "QA PASS does not authorize",
            "network/runtime witnesses",
            "Project metadata",
        ):
            self.assertIn(marker, text)

    def test_codex_quota_block_is_not_treated_as_review_outcome(self):
        lifecycle = LIFECYCLE.read_text(encoding="utf-8")
        dev = DEV_README.read_text(encoding="utf-8")
        for marker in (
            "CODEX_REVIEW_BLOCKED_QUOTA",
            "clean review nor a substantive review failure",
            "merge or release gate",
            "remains unsatisfied",
            "explicit authorized",
        ):
            self.assertIn(marker, lifecycle)
        self.assertIn("CODEX_REVIEW_BLOCKED_QUOTA", dev)
        self.assertIn("does not satisfy or replace the missing", dev)

    def test_project_sync_is_conditional_and_follows_source_disposition(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        migration = text.split("## Migration lifecycle", 1)[1].split(
            "## Pull-request disposition", 1
        )[0]
        self.assertIn("only when that separate mutation is authorized", migration)
        self.assertLess(
            migration.index("source disposition"),
            migration.index("Project synchronization"),
        )

    def test_root_readme_links_lifecycle_policy_and_canonical_qa(self):
        text = ROOT_README.read_text(encoding="utf-8")
        self.assertIn("docs/operations/lifecycle.md", text)
        self.assertIn("tools/dev/check", text)


if __name__ == "__main__":
    unittest.main()
