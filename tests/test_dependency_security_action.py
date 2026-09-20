from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTION_DIR = ROOT / ".github" / "actions" / "dependency-security"
ACTION = ACTION_DIR / "action.yml"
SCRIPT = ACTION_DIR / "dependency_security.py"
LOCK = ACTION_DIR / "requirements.txt"


class DependencySecurityActionContractTest(unittest.TestCase):
    def test_action_metadata_is_composite_no_secret_surface(self):
        text = ACTION.read_text()
        self.assertIn("using: composite", text)
        self.assertIn("inputs-file:", text)
        self.assertIn("receipt-path:", text)
        self.assertIn('python "$GITHUB_ACTION_PATH/dependency_security.py"', text)
        self.assertNotIn("secrets", text.lower())
        self.assertNotIn("permissions:", text)

    def test_action_script_is_valid_python_and_uses_action_owned_lock(self):
        result = subprocess.run(
            ["python3", "-m", "py_compile", str(SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        text = SCRIPT.read_text()
        self.assertIn('os.environ.get("GITHUB_ACTION_PATH"', text)
        self.assertIn('os.environ.get("DEPENDENCY_SECURITY_INPUTS"', text)
        self.assertIn('TOOL_LOCK = ACTION_PATH / "requirements.txt"', text)
        self.assertNotIn('Path("requirements/ci-dependency-security.txt")', text)

    def test_action_owns_same_tool_integrity_pins(self):
        text = SCRIPT.read_text()
        self.assertIn('OSV_VERSION = "2.6.0"', text)
        self.assertIn(
            'OSV_SHA256 = "ca69b3d3cd08f889a49dc0a383122f71cc528b83803671df5fd874d97485b108"',
            text,
        )
        self.assertIn('PIP_AUDIT_VERSION = "2.10.1"', text)
        hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})", LOCK.read_text())
        self.assertEqual(len(hashes), 29)
        self.assertEqual(len(set(hashes)), 29)

    def test_action_script_preserves_receipt_status_contract(self):
        text = SCRIPT.read_text()
        for marker in (
            "DEPENDENCY_COLLECTION_FAILED",
            "VULNERABILITY_SOURCE_UNAVAILABLE",
            "TOOL_INTEGRITY_FAILED",
            "VULNERABILITY_FOUND",
            "CLEAN_AT_QUERY_TIME",
        ):
            self.assertIn(marker, text)

    def test_workflow_security_includes_composite_action_surface(self):
        text = (ROOT / "tools" / "ci" / "workflow-security").read_text()
        self.assertIn('zizmor" --offline --format plain .github', text)
        self.assertNotIn('zizmor" --offline --format plain .github/workflows', text)


if __name__ == "__main__":
    unittest.main()
