from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "tools" / "dev"


class DevQualityGateContractTest(unittest.TestCase):
    def test_expected_tooling_files_exist(self):
        expected = {"bootstrap.sh", "check", "edit", "README.md"}
        self.assertTrue(DEV.is_dir())
        self.assertEqual({p.name for p in DEV.iterdir()}, expected)

    def test_bootstrap_is_posix_and_pinned(self):
        text = (DEV / "bootstrap.sh").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/bin/sh\n"))
        for marker in (
            "MICRO_VERSION=2.0.15",
            "RUFF_VERSION=0.16.6",
            "SHELLCHECK_VERSION=0.11.0",
            "SHFMT_VERSION=3.14.0",
            "sha256sum -c -",
            "/workspace/.local/theseus-dev/bin",
        ):
            self.assertIn(marker, text)
        for forbidden in ("curl | sh", "pip install", "npm install"):
            self.assertNotIn(forbidden, text)

    def test_check_is_changed_file_low_noise_gate(self):
        text = (DEV / "check").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/bin/sh\n"))
        for marker in (
            "origin/main",
            "git diff --name-only",
            "git ls-files --others --exclude-standard",
            "RUFF_CACHE_DIR",
            "/tmp/theseus-dev-cache",
            "--select E9,F63,F7,F82",
            "--severity=warning",
            "--exclude=SC1090,SC1007",
            "legacy shfmt debt",
            "shfmt",
            "jq empty",
            "git diff --check",
            "python3 -m unittest discover",
        ):
            self.assertIn(marker, text)

    def test_edit_uses_tmp_config_and_pinned_micro(self):
        text = (DEV / "edit").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/bin/sh\n"))
        self.assertIn("MICRO_CONFIG_HOME", text)
        self.assertIn("/tmp/theseus-dev-cache", text)
        self.assertIn("$CACHE/micro", text)
        self.assertIn('exec "$DEV_BIN/micro"', text)

    def test_edit_generates_low_noise_inline_linter_config(self):
        text = (DEV / "edit").read_text(encoding="utf-8")
        for marker in (
            "init.lua",
            'removeLinter("ruff")',
            'removeLinter("shellcheck")',
            'removeLinter("shfmt")',
            '"E9,F63,F7,F82"',
            '"--severity=warning"',
            '"--exclude=SC1090,SC1007"',
        ):
            self.assertIn(marker, text)

    def test_runtime_docs_make_execution_language_routing_explicit(self):
        text = (ROOT / "marcopolo" / "README.md").read_text(encoding="utf-8")
        for marker in (
            "Execution-language routing",
            "Direct binary / CLI",
            "POSIX sh",
            "Python",
            "Bash only when Bash semantics are required",
            "tools/dev/check",
        ):
            self.assertIn(marker, text)

    def test_bootstrap_uses_private_mktemp_staging(self):
        text = (DEV / "bootstrap.sh").read_text(encoding="utf-8")
        self.assertIn("mktemp -d", text)
        self.assertNotIn("theseus-dev-bootstrap.$$", text)

    def test_check_fails_closed_without_baseline(self):
        text = (DEV / "check").read_text(encoding="utf-8")
        self.assertIn("baseline ref", text)
        self.assertIn("exit 2", text)

    def test_check_handles_shebang_shell_entrypoints(self):
        text = (DEV / "check").read_text(encoding="utf-8")
        self.assertIn("is_shell_script", text)
        self.assertIn("head -n 1", text)

    def test_check_redirects_python_bytecode_to_tmp_cache(self):
        text = (DEV / "check").read_text(encoding="utf-8")
        self.assertIn("PYTHONPYCACHEPREFIX", text)

    def test_edit_refuses_to_overwrite_existing_init(self):
        text = (DEV / "edit").read_text(encoding="utf-8")
        self.assertIn("existing init.lua", text)

    def test_bootstrap_check_reports_installed_versions_from_isolated_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            bindir = Path(tmp)
            outputs = {
                "micro": "Version: 2.0.15\n",
                "ruff": "ruff 0.16.6\n",
                "shellcheck": "version: 0.11.0\n",
                "shfmt": "v3.14.0\n",
            }
            for name, output in outputs.items():
                tool = bindir / name
                tool.write_text(
                    f"#!/bin/sh\nprintf '%s' '{output}'\n", encoding="utf-8"
                )
                tool.chmod(0o755)
            env = os.environ.copy()
            env["THESEUS_DEV_BIN"] = str(bindir)
            result = subprocess.run(
                [str(DEV / "bootstrap.sh"), "--check"],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for marker in (
            "micro 2.0.15",
            "ruff 0.16.6",
            "shellcheck 0.11.0",
            "shfmt 3.14.0",
        ):
            self.assertIn(marker, result.stdout)


if __name__ == "__main__":
    unittest.main()
