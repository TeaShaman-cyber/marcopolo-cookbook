import hashlib
import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "azure-cli" / "az.sh"


class AzureCliMaterializerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.cache = self.base / "cache"

    def tearDown(self):
        self.tmp.cleanup()

    def _make_deb(self, *, complete=True, version="2.91.0"):
        tree = self.base / "pkg"
        if tree.exists():
            shutil.rmtree(tree)
        (tree / "DEBIAN").mkdir(parents=True)
        (tree / "DEBIAN" / "control").write_text(
            textwrap.dedent(
                """                Package: azure-cli-test
                Version: 1.0
                Architecture: amd64
                Maintainer: tests
                Description: Azure CLI materializer fixture
                """
            ),
            encoding="utf-8",
        )
        az_bin = tree / "opt" / "az" / "bin"
        az_bin.mkdir(parents=True)

        python = az_bin / "python3.14"
        python.write_text(
            '#!/bin/sh\nscript=$1\nshift\nexec /bin/sh "$script" "$@"\n',
            encoding="utf-8",
        )
        python.chmod(python.stat().st_mode | stat.S_IXUSR)

        if complete:
            az = az_bin / "az"
            az.write_text(
                textwrap.dedent(
                    f"""                    #!/bin/sh
                    if [ "$1" = "version" ]; then
                        printf '%s\n' '{{"azure-cli":"{version}","azure-cli-core":"{version}"}}'
                        exit 0
                    fi
                    printf 'ARGS'
                    for arg in "$@"; do
                        printf ' <%s>' "$arg"
                    done
                    printf '\n'
                    """
                ),
                encoding="utf-8",
            )
            az.chmod(az.stat().st_mode | stat.S_IXUSR)

        deb = self.base / "azure-cli-test.deb"
        subprocess.run(
            ["dpkg-deb", "--build", str(tree), str(deb)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        sha = hashlib.sha256(deb.read_bytes()).hexdigest()
        return deb, sha

    def _run(self, deb, sha, *args):
        env = os.environ.copy()
        env.update(
            {
                "AZURE_CLI_PACKAGE": str(deb),
                "AZURE_CLI_PACKAGE_SHA256": sha,
                "AZURE_CLI_EXPECTED_VERSION": "2.91.0",
                "AZURE_CLI_RUNTIME_ID": "azure-cli-test",
                "AZURE_CLI_CACHE_BASE": str(self.cache),
            }
        )
        return subprocess.run(
            [str(WRAPPER), *args],
            text=True,
            capture_output=True,
            env=env,
        )

    def test_cold_materialization_and_argument_passthrough(self):
        deb, sha = self._make_deb()
        proc = self._run(deb, sha, "cloud", "show", "--name", "AzureCloud")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            proc.stdout.strip(), "ARGS <cloud> <show> <--name> <AzureCloud>"
        )
        self.assertTrue(
            (self.cache / "azure-cli-test" / "opt" / "az" / "bin" / "az").exists()
        )

    def test_warm_cache_reuse_does_not_require_package(self):
        deb, sha = self._make_deb()
        first = self._run(deb, sha, "cloud", "show")
        self.assertEqual(first.returncode, 0, first.stderr)
        deb.unlink()
        second = self._run(deb, sha, "cloud", "show")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stdout.strip(), "ARGS <cloud> <show>")

    def test_checksum_mismatch_fails_closed(self):
        deb, _ = self._make_deb()
        proc = self._run(deb, "0" * 64, "version")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("checksum", proc.stderr.lower())
        self.assertFalse((self.cache / "azure-cli-test").exists())

    def test_incomplete_extraction_fails_closed(self):
        deb, sha = self._make_deb(complete=False)
        proc = self._run(deb, sha, "version")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("incomplete", proc.stderr.lower())
        self.assertFalse((self.cache / "azure-cli-test").exists())


if __name__ == "__main__":
    unittest.main()
