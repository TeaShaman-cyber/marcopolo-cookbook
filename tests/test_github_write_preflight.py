import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "github-write-preflight.sh"


class GitHubWritePreflightTests(unittest.TestCase):
    def test_missing_write_profile_fails_before_any_git_probe(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            fake_git = tmp / "git"
            fake_git.write_text("#!/bin/sh\necho SHOULD_NOT_RUN >&2\nexit 91\n")
            fake_git.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "GH_WRITE_CONFIG": str(tmp / "missing-gh-write"),
                    "GITHUB_GIT_AUTH": str(ROOT / "github-git-auth.sh"),
                    "PATH": f"{tmp}:{env['PATH']}",
                }
            )
            cp = subprocess.run(
                [str(SCRIPT), "--check"], env=env, text=True, capture_output=True
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("GH_WRITE_PREFLIGHT BLOCKED stage=profile", cp.stderr)
            self.assertNotIn("SHOULD_NOT_RUN", cp.stderr)

    def test_check_delegates_to_cookbook_git_auth_after_profile_exists(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            write_cfg = tmp / "gh-write"
            write_cfg.mkdir()
            (write_cfg / "hosts.yml").write_text("synthetic\n")
            auth = tmp / "auth-check"
            auth.write_text('#!/bin/sh\n[ "$1" = --check ] || exit 92\necho AUTH_OK\n')
            auth.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {"GH_WRITE_CONFIG": str(write_cfg), "GITHUB_GIT_AUTH": str(auth)}
            )
            cp = subprocess.run(
                [str(SCRIPT), "--check"], env=env, text=True, capture_output=True
            )
            self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertIn("GH_WRITE_PREFLIGHT VERIFIED", cp.stdout)


if __name__ == "__main__":
    unittest.main()
