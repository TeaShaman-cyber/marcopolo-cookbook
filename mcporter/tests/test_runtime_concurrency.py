import hashlib
import os
import pathlib
import subprocess
import tarfile
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENSURE = ROOT / "mcporter" / "scripts" / "ensure-runtime.sh"

class RuntimeConcurrencyTest(unittest.TestCase):
    def test_two_cold_starts_publish_one_valid_cache(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            tool = td / "tool"
            bundles = tool / "runtime" / "bundles"
            stage = td / "stage"
            (stage / "node" / "bin").mkdir(parents=True)
            (stage / "workbench" / "node_modules" / "mcporter" / "dist").mkdir(parents=True)
            bundles.mkdir(parents=True)
            (tool / "runtime" / "versions.env").write_text("NODE_VERSION=v-test\nMCPORTER_VERSION=0.test\nRUNTIME_BUNDLE=test-bundle\n")
            node = stage / "node" / "bin" / "node"
            node.write_text("#!/usr/bin/env bash\nif [[ \"$1\" == \"--version\" ]]; then echo v-test; else echo 0.test; fi\n")
            node.chmod(0o755)
            (stage / "workbench" / "node_modules" / "mcporter" / "dist" / "cli.js").write_text("")
            archive = bundles / "test-bundle.tar.gz"
            with tarfile.open(archive, "w:gz") as tf:
                tf.add(stage / "node", arcname="node")
                tf.add(stage / "workbench", arcname="workbench")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            (bundles / "test-bundle.tar.gz.sha256").write_text(f"{digest}  test-bundle.tar.gz\n")
            env = os.environ.copy()
            env["MCPORTER_ROOT"] = str(tool)
            env["TMPDIR"] = str(td / "tmp")
            a = subprocess.Popen([str(ENSURE)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            b = subprocess.Popen([str(ENSURE)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            ao, ae = a.communicate(timeout=10)
            bo, be = b.communicate(timeout=10)
            self.assertEqual(a.returncode, 0, ae)
            self.assertEqual(b.returncode, 0, be)
            self.assertEqual(ao.strip(), bo.strip())
            cache = pathlib.Path(ao.strip())
            self.assertTrue((cache / "node" / "bin" / "node").is_file())
            version = subprocess.check_output([str(cache / "node" / "bin" / "node"), "--version"], text=True).strip()
            self.assertEqual(version, "v-test")
            self.assertTrue((cache / "workbench" / "node_modules" / "mcporter" / "dist" / "cli.js").is_file())

if __name__ == "__main__":
    unittest.main()
