import importlib.util
import json
import os
import pathlib
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "local_projection.py"
SPEC = importlib.util.spec_from_file_location("local_projection", MODULE_PATH)
assert SPEC and SPEC.loader
lp = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lp
SPEC.loader.exec_module(lp)


class LocalProjectionTests(unittest.TestCase):
    A = "a" * 64
    B = "b" * 64

    def make_corpus(self, root: pathlib.Path, ids=(A,)) -> pathlib.Path:
        corpus = root / "corpus"
        accepted = corpus / "ledger" / "accepted"
        accepted.mkdir(parents=True)
        for artifact_id in ids:
            (accepted / f"{artifact_id}.json").write_text("{}\n", encoding="utf-8")
        self.write_db(corpus / "corpus.sqlite3", ids)
        return corpus

    def write_db(self, path: pathlib.Path, ids) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        try:
            conn.execute("CREATE TABLE artifacts (sha256 TEXT PRIMARY KEY)")
            conn.executemany(
                "INSERT INTO artifacts(sha256) VALUES (?)", [(x,) for x in ids]
            )
            conn.commit()
        finally:
            conn.close()

    def add_artifact(self, corpus: pathlib.Path, artifact_id: str) -> None:
        (corpus / "ledger" / "accepted" / f"{artifact_id}.json").write_text(
            "{}\n", encoding="utf-8"
        )
        conn = sqlite3.connect(corpus / "corpus.sqlite3")
        try:
            conn.execute("INSERT INTO artifacts(sha256) VALUES (?)", (artifact_id,))
            conn.commit()
        finally:
            conn.close()

    def test_refresh_then_current_and_cache_is_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            corpus = self.make_corpus(root)
            cache = root / "cache"
            first = lp.ensure_local_projection(corpus, cache)
            second = lp.ensure_local_projection(corpus, cache)
            self.assertEqual(first["status"], "REFRESHED")
            self.assertEqual(second["status"], "CURRENT")
            self.assertEqual(first["generation"], second["generation"])
            db = pathlib.Path(first["root"]) / "corpus.sqlite3"
            self.assertFalse(db.stat().st_mode & stat.S_IWUSR)

    def test_accepted_set_change_refreshes_generation(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            corpus = self.make_corpus(root)
            cache = root / "cache"
            first = lp.ensure_local_projection(corpus, cache)
            self.add_artifact(corpus, self.B)
            second = lp.ensure_local_projection(corpus, cache)
            self.assertEqual(second["status"], "REFRESHED")
            self.assertNotEqual(first["generation"], second["generation"])
            self.assertEqual(second["accepted_count"], 2)

    def test_source_db_rewrite_with_same_membership_refreshes(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            corpus = self.make_corpus(root)
            cache = root / "cache"
            first = lp.ensure_local_projection(corpus, cache)
            replacement = corpus / "replacement.sqlite3"
            self.write_db(replacement, (self.A,))
            os.replace(replacement, corpus / "corpus.sqlite3")
            second = lp.ensure_local_projection(corpus, cache)
            self.assertEqual(second["status"], "REFRESHED")
            self.assertNotEqual(first["generation"], second["generation"])

    def test_interrupted_publication_state_is_repaired(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            corpus = self.make_corpus(root)
            cache = root / "cache"
            first = lp.ensure_local_projection(corpus, cache)
            paths = lp._cache_paths(corpus, cache)
            stale_meta = paths["meta"].read_bytes()
            self.add_artifact(corpus, self.B)
            candidate = paths["root"] / "manual.sqlite3"
            lp._backup_sqlite(corpus / "corpus.sqlite3", candidate)
            os.chmod(candidate, 0o444)
            os.replace(candidate, paths["db"])
            # Simulate crash before metadata publication: old metadata remains.
            self.assertEqual(paths["meta"].read_bytes(), stale_meta)
            repaired = lp.ensure_local_projection(corpus, cache)
            self.assertEqual(repaired["status"], "REFRESHED")
            self.assertNotEqual(first["generation"], repaired["generation"])
            self.assertTrue(lp._cache_is_current(paths, lp.observe_generation(corpus)))

    def test_concurrent_refreshers_share_one_published_cache(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            corpus = self.make_corpus(root)
            cache = root / "cache"
            cmd = [
                "python3",
                str(MODULE_PATH),
                "--corpus",
                str(corpus),
                "--cache-root",
                str(cache),
                "--json",
            ]
            p1 = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            p2 = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            out1, err1 = p1.communicate(timeout=10)
            out2, err2 = p2.communicate(timeout=10)
            self.assertEqual(p1.returncode, 0, err1)
            self.assertEqual(p2.returncode, 0, err2)
            statuses = {json.loads(out1)["status"], json.loads(out2)["status"]}
            self.assertIn("REFRESHED", statuses)
            self.assertTrue(statuses <= {"REFRESHED", "CURRENT"})
            paths = lp._cache_paths(corpus, cache)
            self.assertTrue(lp._cache_is_current(paths, lp.observe_generation(corpus)))

    def test_paths_with_spaces_and_question_mark_use_readonly_uri_safely(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "space ? corpus root"
            corpus = self.make_corpus(root)
            cache = root / "cache space ?"
            result = lp.ensure_local_projection(corpus, cache)
            self.assertEqual(result["status"], "REFRESHED")
            self.assertTrue((pathlib.Path(result["root"]) / "corpus.sqlite3").is_file())

    def test_symlink_cache_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            corpus = self.make_corpus(root)
            cache = root / "cache"
            paths = lp._cache_paths(corpus, cache)
            target = root / "other"
            target.mkdir()
            paths["root"].parent.mkdir(parents=True)
            paths["root"].symlink_to(target, target_is_directory=True)
            with self.assertRaises(lp.LocalProjectionError) as ctx:
                lp.ensure_local_projection(corpus, cache)
            self.assertEqual(ctx.exception.code, "CACHE_ROOT_UNSAFE")

    def test_active_source_mutation_avoids_refresh(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            corpus = self.make_corpus(root)
            cache = root / "cache"
            (corpus / "mutation.lock").mkdir()
            with self.assertRaises(lp.LocalProjectionError) as ctx:
                lp.ensure_local_projection(corpus, cache)
            self.assertEqual(ctx.exception.code, "SOURCE_MUTATION_ACTIVE")
            paths = lp._cache_paths(corpus, cache)
            self.assertFalse(paths["db"].exists())

    def test_ledger_db_mismatch_fails_without_publishing_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            corpus = self.make_corpus(root)
            cache = root / "cache"
            (corpus / "ledger" / "accepted" / f"{self.B}.json").write_text(
                "{}\n", encoding="utf-8"
            )
            with self.assertRaises(lp.LocalProjectionError) as ctx:
                lp.ensure_local_projection(corpus, cache)
            self.assertEqual(ctx.exception.code, "CANDIDATE_MEMBERSHIP_MISMATCH")
            paths = lp._cache_paths(corpus, cache)
            self.assertFalse(paths["db"].exists())
            self.assertFalse(paths["meta"].exists())


if __name__ == "__main__":
    unittest.main()
