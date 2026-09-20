from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
REUSABLE = ROOT / ".github" / "workflows" / "reusable-dependency-security.yml"
ENDPOINT = ROOT / "tools" / "ci" / "dependency-security"
INPUTS = ROOT / "config" / "dependency-security.inputs"
LOCK = ROOT / "requirements" / "ci-dependency-security.txt"


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
                "pip-hashed requirements/ci-dependency-security.txt",
            ],
        )
        self.assertNotIn(".worktrees", INPUTS.read_text())
        self.assertNotIn("*", "\n".join(rows))

    def test_endpoint_is_valid_python_and_pins_tool_integrity(self):
        result = subprocess.run(
            ["python3", "-m", "py_compile", str(ENDPOINT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        text = ENDPOINT.read_text()
        self.assertIn('OSV_VERSION = "2.6.0"', text)
        self.assertIn(
            'OSV_SHA256 = "ca69b3d3cd08f889a49dc0a383122f71cc528b83803671df5fd874d97485b108"',
            text,
        )
        self.assertIn('PIP_AUDIT_VERSION = "2.10.1"', text)
        self.assertIn("TOOL_INTEGRITY_FAILED", text)
        self.assertIn("--require-hashes", text)

    def test_endpoint_uses_explicit_osv_lockfiles_not_recursive_scan(self):
        text = ENDPOINT.read_text()
        self.assertIn('"--lockfile"', text)
        self.assertIn('"--no-resolve"', text)
        self.assertNotIn('"--recursive"', text)
        self.assertNotIn('"-r", "."', text)

    def test_endpoint_distinguishes_collection_source_findings_and_clean(self):
        text = ENDPOINT.read_text()
        for marker in (
            "DEPENDENCY_COLLECTION_FAILED",
            "VULNERABILITY_SOURCE_UNAVAILABLE",
            "TOOL_INTEGRITY_FAILED",
            "VULNERABILITY_FOUND",
            "CLEAN_AT_QUERY_TIME",
        ):
            self.assertIn(marker, text)
        self.assertIn('"--dry-run"', text)

    def test_pip_audit_runtime_lock_is_fully_hash_pinned(self):
        text = LOCK.read_text()
        self.assertIn("pip_audit==2.10.1", text)
        self.assertIn("pip==26.2.1", text)
        hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})", text)
        package_lines = [
            line
            for line in text.splitlines()
            if line and not line.startswith("#") and "==" in line
        ]
        self.assertEqual(len(package_lines), 29)
        self.assertEqual(len(hashes), 29)
        self.assertEqual(len(set(hashes)), 29)

    def test_candidate_has_no_relative_self_consumer(self):
        self.assertFalse(
            (ROOT / ".github" / "workflows" / "dependency-security.yml").exists()
        )


if __name__ == "__main__":
    unittest.main()
