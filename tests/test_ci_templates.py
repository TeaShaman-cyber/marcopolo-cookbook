from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / ".github" / "workflows" / "reusable-canonical-qa.yml"
HEAVY = ROOT / ".github" / "workflows" / "reusable-heavy-python.yml"
LADDER = ROOT / "docs" / "operations" / "verification-ladder.md"


class ReusableCiTemplateContractTest(unittest.TestCase):
    def test_templates_exist_and_are_workflow_call_only(self):
        for path in (CANONICAL, HEAVY):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                text = path.read_text()
                self.assertIn('"on":', text)
                self.assertIn("workflow_call:", text)
                self.assertNotIn("pull_request:", text)
                self.assertNotIn("push:", text)
                self.assertNotIn("schedule:", text)

    def test_templates_are_read_only_and_action_revisions_are_pinned(self):
        sha_use = re.compile(r"uses:\s+[^@\s]+@[0-9a-f]{40}$", re.MULTILINE)
        for path in (CANONICAL, HEAVY):
            with self.subTest(path=path.name):
                text = path.read_text()
                self.assertIn("permissions:\n  contents: read", text)
                self.assertNotRegex(text, r"contents:\s+write")
                uses = [line for line in text.splitlines() if "uses:" in line]
                self.assertTrue(uses)
                for line in uses:
                    self.assertRegex(line.strip(), sha_use)

    def test_checkout_does_not_persist_credentials(self):
        for path in (CANONICAL, HEAVY):
            with self.subTest(path=path.name):
                text = path.read_text()
                checkout = text.split("uses: actions/checkout@", 1)[1].split(
                    "- name:", 1
                )[0]
                self.assertIn("persist-credentials: false", checkout)

    def test_setup_python_uses_action_owned_hyphenated_input_name(self):
        for path in (CANONICAL, HEAVY):
            with self.subTest(path=path.name):
                text = path.read_text()
                setup = text.split("uses: actions/setup-python@", 1)[1].split(
                    "- name:", 1
                )[0]
                self.assertIn("python-version: ${{ inputs.python_version }}", setup)
                self.assertNotIn("python_version:", setup)

    def test_acceptance_templates_do_not_soften_failures(self):
        for path in (CANONICAL, HEAVY):
            with self.subTest(path=path.name):
                self.assertNotIn("continue-on-error", path.read_text())

    def test_templates_emit_exact_execution_identity(self):
        for path, profile in ((CANONICAL, "canonical-qa"), (HEAVY, "heavy-python")):
            with self.subTest(path=path.name):
                text = path.read_text()
                self.assertIn(f"VERIFICATION_PROFILE: {profile}", text)
                for marker in (
                    "github.repository",
                    "github.sha",
                    "github.run_id",
                    "github.run_attempt",
                    "github.workflow_ref",
                    "github.workflow_sha",
                ):
                    self.assertIn(marker, text)

    def test_heavy_profile_preserves_interrupt_and_termination_semantics(self):
        text = HEAVY.read_text()
        self.assertIn("trap cleanup_heartbeat EXIT", text)
        self.assertIn("trap 'cleanup_heartbeat; exit 130' INT", text)
        self.assertIn("trap 'cleanup_heartbeat; exit 143' TERM", text)
        self.assertIn("trap - EXIT INT TERM", text)

    def test_heavy_profile_telemetry_is_lightweight_and_sixty_second(self):
        text = HEAVY.read_text()
        self.assertIn("sleep 60", text)
        self.assertIn("heavy_python_resource_baseline", text)
        self.assertIn("heavy_python_heartbeat", text)
        self.assertIn("heavy_python_resource_final", text)
        snapshot = text.split("emit_resource_snapshot() {", 1)[1].split(
            "heartbeat() {", 1
        )[0]
        self.assertIn("/proc/meminfo", snapshot)
        self.assertIn("df -Pk /", snapshot)
        heartbeat = text.split("heartbeat() {", 1)[1].split("}", 1)[0]
        for forbidden in ("du ", "find ", "git ", "gh ", "curl ", "lake "):
            self.assertNotIn(forbidden, heartbeat)

    def test_workflow_input_identifiers_are_safe_for_dot_notation(self):
        bad = re.compile(r"inputs\.[A-Za-z_][A-Za-z0-9_]*-[A-Za-z0-9_-]+")
        for path in (CANONICAL, HEAVY):
            with self.subTest(path=path.name):
                self.assertIsNone(bad.search(path.read_text()))

    def test_templates_have_bounded_timeouts(self):
        self.assertIn("timeout-minutes: 15", CANONICAL.read_text())
        self.assertIn("timeout-minutes: 20", HEAVY.read_text())

    def test_canonical_profile_calls_repository_owned_qa(self):
        text = CANONICAL.read_text()
        self.assertIn('default: "tools/dev/check"', text)
        self.assertIn("QA_ENDPOINT", text)
        self.assertIn("missing canonical QA endpoint", text)
        self.assertIn('bash "$QA_ENDPOINT"', text)

    def test_heavy_profile_requires_caller_owned_hash_lock_and_endpoint(self):
        text = HEAVY.read_text()
        self.assertIn('default: "requirements/ci-heavy.txt"', text)
        self.assertIn('default: "tools/ci/heavy-python"', text)
        self.assertIn("--require-hashes", text)
        self.assertIn("missing heavy-analysis lock", text)
        self.assertIn("missing heavy-analysis endpoint", text)
        self.assertLess(
            text.index("Validate caller heavy-analysis contract"),
            text.index("Set up Python"),
        )
        for forbidden in ("semgrep", "mypy", "bandit", "pyright"):
            self.assertNotIn(forbidden, text.lower())

    def test_ladder_separates_local_ci_and_codespace_roles(self):
        text = LADDER.read_text()
        for marker in (
            "L0 — MarcoPolo",
            "L1 — GitHub Actions",
            "L2 — Codespace",
            "debugging surface, not acceptance",
            "recurring cross-project class",
            "Codex quota or model unavailability",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
