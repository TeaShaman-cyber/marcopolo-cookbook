from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REUSABLE = ROOT / ".github" / "workflows" / "reusable-dependency-security.yml"
INPUTS = ROOT / "config" / "dependency-security.inputs"


class DependencySecurityProfileContractTest(unittest.TestCase):
    def test_reusable_profile_is_read_only_exact_source_and_bounded(self):
        text = REUSABLE.read_text()
        self.assertIn('"on":\n  workflow_call:', text)
        self.assertIn("permissions:\n  contents: read", text)
        self.assertIn("timeout-minutes: 20", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("github.event.pull_request.head.sha || github.sha", text)
        self.assertIn("QA_SOURCE_MISMATCH", text)
        self.assertNotIn("continue-on-error", text)
        self.assertNotIn("secrets:", text)

    def test_reusable_profile_always_emits_machine_readable_receipt(self):
        text = REUSABLE.read_text()
        self.assertIn("DEPENDENCY_SECURITY_RECEIPT", text)
        self.assertIn("dependency-security-receipt.json", text)
        self.assertIn("DEPENDENCY_SECURITY_RECEIPT_MISSING", text)
        self.assertIn('cat "$DEPENDENCY_SECURITY_RECEIPT"', text)
        self.assertIn("if: always()", text)

    def test_reusable_profile_pins_shared_action_and_caller_owns_only_inputs(self):
        text = REUSABLE.read_text()
        self.assertIn(
            "uses: TeaShaman-cyber/marcopolo-cookbook/.github/actions/"
            "dependency-security@28ca86bf93a80e37361f171f32080892be8c6ba8",
            text,
        )
        self.assertIn("inputs_file:", text)
        self.assertIn('default: "config/dependency-security.inputs"', text)
        self.assertNotIn("analysis_endpoint:", text)
        self.assertNotIn("tools/ci/dependency-security", text)

    def test_dependency_inputs_are_explicit_and_do_not_scan_worktrees(self):
        rows = [
            line.strip()
            for line in INPUTS.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(
            rows,
            [
                "osv-lockfile mcporter/package-lock.json",
                "osv-lockfile mcpjam-cli/package-lock.json",
                "pip-requirements marcopolo/requirements-python.txt",
                "pip-hashed requirements/ci-workflow-security.txt",
            ],
        )
        self.assertNotIn(".worktrees", INPUTS.read_text())
        self.assertNotIn("*", "\n".join(rows))

    def test_zero_copy_caller_has_no_generic_scanner_runtime_duplicates(self):
        self.assertFalse((ROOT / "tools" / "ci" / "dependency-security").exists())
        self.assertFalse(
            (ROOT / "requirements" / "ci-dependency-security.txt").exists()
        )
        self.assertTrue(
            (
                ROOT
                / ".github"
                / "actions"
                / "dependency-security"
                / "dependency_security.py"
            ).is_file()
        )
        self.assertTrue(
            (
                ROOT
                / ".github"
                / "actions"
                / "dependency-security"
                / "requirements.txt"
            ).is_file()
        )

    def test_self_consumer_pins_promoted_profile(self):
        path = ROOT / ".github" / "workflows" / "dependency-security.yml"
        self.assertTrue(path.is_file())
        text = path.read_text()
        expected = (
            "uses: TeaShaman-cyber/marcopolo-cookbook/.github/workflows/"
            "reusable-dependency-security.yml@a6c1a24b642585a6d4dc1a87d2eef6f61aee965a"
        )
        self.assertIn(expected, text)
        self.assertNotIn(
            "uses: ./.github/workflows/reusable-dependency-security.yml", text
        )
        self.assertNotIn("@main", text)
        self.assertIn("inputs_file: config/dependency-security.inputs", text)
        self.assertNotIn("analysis_endpoint:", text)
        self.assertIn("permissions:\n  contents: read", text)


if __name__ == "__main__":
    unittest.main()
