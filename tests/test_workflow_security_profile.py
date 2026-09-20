from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
REUSABLE = ROOT / ".github" / "workflows" / "reusable-workflow-security.yml"
CONSUMER = ROOT / ".github" / "workflows" / "workflow-security.yml"
ENDPOINT = ROOT / "tools" / "ci" / "workflow-security"
LOCK = ROOT / "requirements" / "ci-workflow-security.txt"


class WorkflowSecurityProfileContractTest(unittest.TestCase):
    def test_reusable_profile_is_read_only_exact_source_and_bounded(self):
        text = REUSABLE.read_text()
        self.assertIn('"on":\n  workflow_call:', text)
        self.assertIn("permissions:\n  contents: read", text)
        self.assertIn("timeout-minutes: 15", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("github.event.pull_request.head.sha || github.sha", text)
        self.assertIn("QA_SOURCE_MISMATCH", text)
        self.assertNotIn("continue-on-error", text)
        self.assertNotIn("secrets:", text)

    def test_consumer_is_advisory_surface_and_calls_local_exact_commit_profile(self):
        text = CONSUMER.read_text()
        self.assertIn("pull_request:", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("push:", text)
        self.assertIn("uses: ./.github/workflows/reusable-workflow-security.yml", text)
        self.assertIn("permissions:\n  contents: read", text)

    def test_endpoint_is_valid_posix_shell_and_explicitly_offline(self):
        result = subprocess.run(
            ["sh", "-n", str(ENDPOINT)], capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        text = ENDPOINT.read_text()
        self.assertIn('zizmor" --offline', text)
        self.assertIn("WORKFLOW_SECURITY_RESULT", text)
        self.assertIn("WORKFLOW_SECURITY_PASS", text)

    def test_actionlint_version_url_and_checksum_are_immutable(self):
        text = ENDPOINT.read_text()
        self.assertIn("ACTIONLINT_VERSION=1.7.12", text)
        self.assertIn(
            "ACTIONLINT_SHA256=8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8",
            text,
        )
        self.assertIn("releases/download/v${ACTIONLINT_VERSION}", text)
        self.assertIn("WORKFLOW_SECURITY_TOOL_MISMATCH", text)

    def test_zizmor_lock_is_single_exact_hash_pinned_wheel(self):
        text = LOCK.read_text()
        self.assertIn("zizmor==1.30.1", text)
        hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})", text)
        self.assertEqual(
            hashes,
            ["eee12266b793cb87ad4a7e3af2e72404f8a63e3de5eb099b80bf7b1cfd232a8e"],
        )
        self.assertIn("--require-hashes", ENDPOINT.read_text())

    def test_endpoint_preserves_interrupt_and_termination_semantics(self):
        text = ENDPOINT.read_text()
        self.assertIn("trap cleanup EXIT", text)
        self.assertIn("trap 'cleanup; exit 130' INT", text)
        self.assertIn("trap 'cleanup; exit 143' TERM", text)

    def test_endpoint_uses_runner_temp_not_workspace_for_tool_install(self):
        text = ENDPOINT.read_text()
        self.assertIn("TMP_BASE=${RUNNER_TEMP:-/tmp}", text)
        self.assertIn("mktemp -d", text)
        self.assertNotIn("/workspace/.", text)


if __name__ == "__main__":
    unittest.main()
