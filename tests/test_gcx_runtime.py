import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "grafana" / "gcx.sh"
LOGIN = ROOT / "grafana" / "gcx-oauth-relay.sh"


class GrafanaRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        bin_dir = self.base / "bin"
        bin_dir.mkdir()
        cron = bin_dir / "crontab"
        cron.write_text(
            '#!/bin/sh\nif [ "$1" = "-l" ]; then cat "$GCX_TEST_CRONTAB" 2>/dev/null || exit 1; else cp "$1" "$GCX_TEST_CRONTAB"; fi\n'
        )
        cron.chmod(0o700)
        ssh = bin_dir / "ssh"
        ssh.write_text("#!/bin/sh\nexit 0\n")
        ssh.chmod(0o700)
        self.env = {
            **os.environ,
            "PATH": f"{bin_dir}:" + os.environ["PATH"],
            "GCX_TEST_CRONTAB": str(self.base / "crontab"),
            "GCX_AUTH_DIR": str(self.base / "profile"),
            "GCX_BIN": "/bin/true",
            "GCX_HELPER_PATH": str(LOGIN),
            "GCX_RUNTIME_DIR": str(self.base / "runtime"),
        }

    def run_command(self, script, *args, approved=False):
        env = dict(self.env)
        if approved:
            env["GCX_FILE_STORAGE_APPROVED"] = "1"
        else:
            env.pop("GCX_FILE_STORAGE_APPROVED", None)
        return subprocess.run(
            [str(script), *args], env=env, text=True, capture_output=True
        )

    def test_missing_pinned_archive_blocks_install(self):
        result = self.run_command(BOOTSTRAP, "--install")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing_or_linked_artifact", result.stderr)

    def test_checksum_mismatch_blocks_install(self):
        runtime = Path(self.env["GCX_RUNTIME_DIR"])
        archive_dir = runtime / "runtime"
        archive_dir.mkdir(parents=True)
        (archive_dir / "gcx_1.7.1_linux_amd64.tar.gz").write_bytes(b"bad artifact")
        result = self.run_command(BOOTSTRAP, "--install")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksum_mismatch", result.stderr)
        self.assertFalse((runtime / "bin" / "gcx").exists())

    def test_schedule_without_storage_approval_fails_closed(self):
        result = self.run_command(LOGIN, "--schedule")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("file_storage_requires_explicit_approval", result.stderr)
        self.assertFalse(Path(self.env["GCX_TEST_CRONTAB"]).exists())

    def test_scheduled_login_is_idempotent_and_cancellable(self):
        self.assertEqual(
            self.run_command(LOGIN, "--schedule", approved=True).returncode, 0
        )
        self.assertEqual(
            self.run_command(LOGIN, "--schedule", approved=True).returncode, 0
        )
        lines = Path(self.env["GCX_TEST_CRONTAB"]).read_text().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn("GCX_OAUTH_RELAY_ONESHOT", lines[0])
        self.assertEqual(self.run_command(LOGIN, "--cancel").returncode, 0)
        self.assertNotIn(
            "GCX_OAUTH_RELAY_ONESHOT", Path(self.env["GCX_TEST_CRONTAB"]).read_text()
        )
        denied = self.run_command(LOGIN, "--run")
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("approved_schedule_missing", denied.stderr)

    def test_direct_run_without_approved_schedule_fails_closed(self):
        Path(self.env["GCX_AUTH_DIR"]).mkdir()
        result = self.run_command(LOGIN, "--run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_schedule_missing", result.stderr)
        self.assertFalse((Path(self.env["GCX_AUTH_DIR"]) / "config.yaml").exists())


if __name__ == "__main__":
    unittest.main()
