from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTION_DIR = ROOT / ".github/actions/semantic-advisory-mechanics"
sys.path.insert(0, str(ACTION_DIR))

artifact_package = importlib.import_module("artifact_package")
package_freshness = importlib.import_module("package_freshness")
trace_input = importlib.import_module("trace_input")


class SemanticAdvisoryMechanicsTests(unittest.TestCase):
    def _repo(self):
        temp = tempfile.TemporaryDirectory()
        repo = Path(temp.name)
        subprocess.run(["git", "init", "-q", repo], check=True)
        subprocess.run(["git", "-C", repo, "config", "user.name", "test"], check=True)
        subprocess.run(
            ["git", "-C", repo, "config", "user.email", "test@example.invalid"],
            check=True,
        )
        return temp, repo

    def _commit(self, repo: Path, message: str) -> str:
        subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
        subprocess.run(["git", "-C", repo, "commit", "-q", "-m", message], check=True)
        return subprocess.check_output(
            ["git", "-C", repo, "rev-parse", "HEAD"], text=True
        ).strip()

    def test_copied_generic_helpers_match_verified_consumer_hashes(self):
        expected = {
            "trace_input.py": (
                "55e1b73eaacf8dc3291e82332734aaf779049d53204fa8dccd1b3ccf49cc90a4"
            ),
            "package_freshness.py": (
                "0888158453d53769ec50273d616a4976518ea8e3558b7f3385db1c9398f2d21b"
            ),
        }
        for name, digest in expected.items():
            observed = hashlib.sha256((ACTION_DIR / name).read_bytes()).hexdigest()
            self.assertEqual(observed, digest)

    def test_bounded_input_binds_exact_commits_and_degrades(self):
        temp, repo = self._repo()
        self.addCleanup(temp.cleanup)
        (repo / "a.txt").write_text("a\n")
        base = self._commit(repo, "base")
        (repo / "a.txt").write_text("x" * 200 + "\n")
        head = self._commit(repo, "head")

        manifest = trace_input.build_manifest(
            repo,
            base,
            head,
            repo / "trace",
            "owner/repo",
            "pr-1",
            max_files=20,
            max_total_bytes=10,
            max_file_bytes=65536,
        )

        self.assertEqual(manifest["base_sha"], base)
        self.assertEqual(manifest["candidate_sha"], head)
        self.assertEqual(manifest["status"], "DEGRADED")
        self.assertEqual(manifest["skipped"][0]["reason"], "total_byte_budget")

    def test_freshness_distinguishes_stale_from_unknown(self):
        now = datetime(2026, 9, 21, tzinfo=timezone.utc)
        stale = package_freshness.evaluate_freshness(
            now=now,
            built_at="2026-09-20T00:00:00Z",
            expires_at="2026-12-19T00:00:00Z",
            max_age_days=30,
            expiry_warning_days=14,
            pinned_git_sha="a" * 40,
            current_git_sha="b" * 40,
        )
        unknown = package_freshness.evaluate_freshness(
            now=now,
            built_at="2026-09-20T00:00:00Z",
            expires_at="2026-12-19T00:00:00Z",
            max_age_days=30,
            expiry_warning_days=14,
            currentness_errors=["network unavailable"],
        )

        self.assertEqual(stale["status"], "STALE_AVAILABLE")
        self.assertEqual(unknown["status"], "CURRENTNESS_UNKNOWN")

    def test_artifact_identity_rejects_builder_head_mismatch(self):
        package = {
            "artifact_id": 7,
            "artifact_name": "pkg",
            "artifact_digest": "sha256:" + "a" * 64,
            "run_id": 9,
            "builder_head_sha": "b" * 40,
        }
        metadata = {
            "id": 7,
            "name": "pkg",
            "digest": "sha256:" + "a" * 64,
            "expired": False,
            "workflow_run": {"id": 9, "head_sha": "c" * 40},
        }

        with self.assertRaisesRegex(RuntimeError, "builder head"):
            artifact_package.verify_metadata(package, metadata)

    def _make_artifact(self, root: Path) -> tuple[Path, Path]:
        payload = root / "payload"
        payload.mkdir()
        (payload / "build-receipt.json").write_text(
            json.dumps({"status": "BUILT"}) + "\n"
        )

        tar_path = root / "toolchain.tar.gz"
        with tarfile.open(tar_path, "w:gz") as packed:
            packed.add(payload / "build-receipt.json", arcname="build-receipt.json")

        archive = root / "artifact.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.write(tar_path, arcname="toolchain.tar.gz")
        return archive, tar_path

    def test_outer_and_inner_digests_are_verified_before_extract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, tar_path = self._make_artifact(root)
            package = {
                "artifact_id": 7,
                "artifact_name": "pkg",
                "artifact_digest": (
                    "sha256:" + hashlib.sha256(archive.read_bytes()).hexdigest()
                ),
                "run_id": 9,
                "builder_head_sha": "b" * 40,
                "tar_file": "toolchain.tar.gz",
                "tar_sha256": hashlib.sha256(tar_path.read_bytes()).hexdigest(),
            }
            metadata = {
                "id": 7,
                "name": "pkg",
                "digest": package["artifact_digest"],
                "expired": False,
                "workflow_run": {"id": 9, "head_sha": "b" * 40},
            }

            receipt = artifact_package.verify_and_extract(
                package,
                metadata,
                archive,
                staging_dir=root / "staging",
                runtime_dir=root / "runtime",
            )
            self.assertEqual(receipt["tar_sha256"], package["tar_sha256"])
            self.assertTrue((root / "runtime" / "build-receipt.json").is_file())

            bad = dict(package)
            bad["tar_sha256"] = "0" * 64
            with self.assertRaisesRegex(RuntimeError, "tar sha"):
                artifact_package.verify_and_extract(
                    bad,
                    metadata,
                    archive,
                    staging_dir=root / "bad-staging",
                    runtime_dir=root / "bad-runtime",
                )

    def test_action_contract_contains_no_semantic_policy(self):
        action = (ACTION_DIR / "action.yml").read_text()
        self.assertNotIn("threshold", action)
        self.assertNotIn("corpus", action)
        self.assertNotIn("semantic verdict", action.lower())
        token_expression = "GH_TOKEN: " + chr(36) + "{{ github.token }}"
        self.assertIn(token_expression, action)


if __name__ == "__main__":
    unittest.main()
