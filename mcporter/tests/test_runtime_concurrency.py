import fcntl
import hashlib
import os
import pathlib
import subprocess
import tarfile
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENSURE = ROOT / "mcporter" / "scripts" / "ensure-runtime.sh"

def build_archive(bundles: pathlib.Path, stage: pathlib.Path, name: str = "test-bundle") -> pathlib.Path:
    archive = bundles / f"{name}.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(stage / "node", arcname="node")
        tf.add(stage / "workbench", arcname="workbench")
    return archive

class RuntimeConcurrencyTest(unittest.TestCase):
    def _fixture(self, td: pathlib.Path):
        tool = td / "tool"
        bundles = tool / "runtime" / "bundles"
        stage = td / "stage"
        (stage / "node" / "bin").mkdir(parents=True)
        (stage / "workbench" / "node_modules" / "mcporter" / "dist").mkdir(parents=True)
        bundles.mkdir(parents=True)
        (tool / "runtime" / "versions.env").write_text(
            "NODE_VERSION=v-test\nMCPORTER_VERSION=0.test\nRUNTIME_BUNDLE=test-bundle\n"
        )
        node = stage / "node" / "bin" / "node"
        node.write_text(
            '#!/usr/bin/env bash\nif [[ "$1" == "--version" ]]; then echo v-test; else echo 0.test; fi\n'
        )
        node.chmod(0o755)
        (stage / "workbench" / "node_modules" / "mcporter" / "dist" / "cli.js").write_text("")
        return tool, bundles, stage

    def test_two_cold_starts_publish_one_valid_cache(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = pathlib.Path(td_s)
            tool, bundles, stage = self._fixture(td)
            archive = build_archive(bundles, stage)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            (bundles / "test-bundle.tar.gz.sha256").write_text(
                f"{digest}  test-bundle.tar.gz\n"
            )
            env = os.environ.copy()
            env["MCPORTER_ROOT"] = str(tool)
            env["TMPDIR"] = str(td / "tmp")
            a = subprocess.Popen(
                [str(ENSURE)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            b = subprocess.Popen(
                [str(ENSURE)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            ao, ae = a.communicate(timeout=10)
            bo, be = b.communicate(timeout=10)
            self.assertEqual(a.returncode, 0, ae)
            self.assertEqual(b.returncode, 0, be)
            self.assertEqual(ao.strip(), bo.strip())
            cache = pathlib.Path(ao.strip())
            self.assertTrue((cache / "node" / "bin" / "node").is_file())
            version = subprocess.check_output(
                [str(cache / "node" / "bin" / "node"), "--version"], text=True
            ).strip()
            self.assertEqual(version, "v-test")
            self.assertTrue(
                (
                    cache
                    / "workbench"
                    / "node_modules"
                    / "mcporter"
                    / "dist"
                    / "cli.js"
                ).is_file()
            )

    def test_cache_root_is_private_before_cached_executables_run(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = pathlib.Path(td_s)
            tool, bundles, stage = self._fixture(td)
            archive = build_archive(bundles, stage)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            (bundles / "test-bundle.tar.gz.sha256").write_text(
                f"{digest}  test-bundle.tar.gz\n"
            )

            tmpdir = td / "tmp"
            uid = os.getuid()
            cache_root = tmpdir / f"marcopolo-mcporter-{uid}"
            cache = cache_root / "test-bundle"
            fake_node = cache / "node" / "bin" / "node"
            fake_cli = cache / "workbench" / "node_modules" / "mcporter" / "dist" / "cli.js"
            fake_node.parent.mkdir(parents=True)
            fake_cli.parent.mkdir(parents=True)
            marker = td / "fake-node-ran"
            fake_node.write_text(
                '#!/usr/bin/env bash\nprintf x > "' + str(marker) + '"\n'
                'if [[ "$1" == "--version" ]]; then echo v-test; else echo 0.test; fi\n'
            )
            fake_node.chmod(0o755)
            fake_cli.write_text("")
            cache_root.chmod(0o777)

            env = os.environ.copy()
            env["MCPORTER_ROOT"] = str(tool)
            env["TMPDIR"] = str(tmpdir)
            proc = subprocess.run(
                [str(ENSURE)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
            )

            self.assertNotEqual(proc.returncode, 0, "insecure pre-existing cache root was accepted")
            self.assertFalse(marker.exists(), "pre-planted cache executable ran before cache root trust was established")

    def test_reader_waits_for_consistent_publication_pair(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = pathlib.Path(td_s)
            tool, bundles, stage = self._fixture(td)
            archive = build_archive(bundles, stage)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            sha = bundles / "test-bundle.tar.gz.sha256"
            sha.write_text("0" * 64 + "  test-bundle.tar.gz\n")

            lock_path = bundles / ".test-bundle.publish.lock"
            with lock_path.open("w") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                env = os.environ.copy()
                env["MCPORTER_ROOT"] = str(tool)
                env["TMPDIR"] = str(td / "tmp")
                proc = subprocess.Popen(
                    [str(ENSURE)],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                )
                time.sleep(0.2)
                self.assertIsNone(
                    proc.poll(),
                    "ensure-runtime read the publication pair while the writer lock was held",
                )
                sha.write_text(f"{digest}  test-bundle.tar.gz\n")
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

            out, err = proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 0, err)
            self.assertTrue(pathlib.Path(out.strip()).exists())

if __name__ == "__main__":
    unittest.main()
