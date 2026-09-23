import json
import os
import pathlib
import sqlite3
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATERIALIZE = ROOT / "materialize-runtime.sh"
ARTIFACT = "a" * 64


class SearchLocalProjectionIntegrationTests(unittest.TestCase):
    def make_corpus(self, root: pathlib.Path) -> pathlib.Path:
        corpus = root / "corpus"
        accepted = corpus / "ledger" / "accepted"
        accepted.mkdir(parents=True)
        (accepted / f"{ARTIFACT}.json").write_text("{}\n", encoding="utf-8")
        conn = sqlite3.connect(corpus / "corpus.sqlite3")
        try:
            conn.execute("CREATE TABLE artifacts (sha256 TEXT PRIMARY KEY)")
            conn.execute("INSERT INTO artifacts(sha256) VALUES (?)", (ARTIFACT,))
            conn.commit()
        finally:
            conn.close()
        return corpus

    def make_implementation(self, root: pathlib.Path) -> pathlib.Path:
        impl = root / "impl"
        pkg = impl / "session_search"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "search.py").write_text(
            "import json,sys\n"
            "i=sys.argv.index('--corpus')\n"
            "print(json.dumps({'corpus':sys.argv[i+1]}, sort_keys=True))\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q", "-b", "main", str(impl)], check=True)
        subprocess.run(["git", "-C", str(impl), "add", "session_search"], check=True)
        env = os.environ.copy()
        env.update(
            {
                "GIT_AUTHOR_NAME": "test",
                "GIT_AUTHOR_EMAIL": "test@example.invalid",
                "GIT_COMMITTER_NAME": "test",
                "GIT_COMMITTER_EMAIL": "test@example.invalid",
            }
        )
        subprocess.run(
            ["git", "-C", str(impl), "commit", "-q", "-m", "fixture"],
            check=True,
            env=env,
        )
        return impl

    def make_runtime(
        self, root: pathlib.Path, corpus: pathlib.Path, impl: pathlib.Path
    ) -> pathlib.Path:
        runtime = root / "runtime"
        subprocess.run(
            [str(MATERIALIZE), str(runtime)], check=True, capture_output=True, text=True
        )
        (runtime / "runtime.env").write_text(
            f"SESSION_SEARCH_CORPUS={corpus}\n"
            f"SESSION_SEARCH_IMPLEMENTATION_ROOT={impl}\n",
            encoding="utf-8",
        )
        return runtime

    def base_env(self, cache_root: pathlib.Path) -> dict[str, str]:
        env = os.environ.copy()
        env["SESSION_SEARCH_CANONICAL_DIR"] = str(ROOT)
        env["SESSION_SEARCH_CANONICAL_REF"] = ""
        env["SESSION_SEARCH_LOCAL_CACHE_ROOT"] = str(cache_root)
        return env

    def test_search_prefers_validated_local_projection(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            corpus = self.make_corpus(root)
            impl = self.make_implementation(root)
            runtime = self.make_runtime(root, corpus, impl)
            cache = root / "cache"
            proc = subprocess.run(
                [str(runtime / "search.sh"), "fixture", "--json"],
                text=True,
                capture_output=True,
                env=self.base_env(cache),
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertNotEqual(payload["corpus"], str(corpus))
            self.assertTrue(pathlib.Path(payload["corpus"]).is_relative_to(cache))
            self.assertEqual(proc.stderr, "")

    def test_explicit_cache_root_wins_over_runtime_env_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            corpus = self.make_corpus(root)
            impl = self.make_implementation(root)
            runtime = self.make_runtime(root, corpus, impl)
            bound_cache = root / "bound-cache"
            with (runtime / "runtime.env").open("a", encoding="utf-8") as handle:
                handle.write(f"SESSION_SEARCH_LOCAL_CACHE_ROOT={bound_cache}\n")
            override_cache = root / "override-cache"
            proc = subprocess.run(
                [str(runtime / "search.sh"), "fixture", "--json"],
                text=True,
                capture_output=True,
                env=self.base_env(override_cache),
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(
                pathlib.Path(payload["corpus"]).is_relative_to(override_cache)
            )
            self.assertFalse(bound_cache.exists())

    def test_active_mutation_lock_uses_explicit_durable_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            corpus = self.make_corpus(root)
            impl = self.make_implementation(root)
            runtime = self.make_runtime(root, corpus, impl)
            cache = root / "cache"
            (corpus / "mutation.lock").mkdir()
            proc = subprocess.run(
                [str(runtime / "search.sh"), "fixture", "--json"],
                text=True,
                capture_output=True,
                env=self.base_env(cache),
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["corpus"], str(corpus))
            self.assertIn("SOURCE_MUTATION_ACTIVE", proc.stderr)

    def test_search_falls_back_to_durable_corpus_when_cache_unavailable(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            corpus = self.make_corpus(root)
            impl = self.make_implementation(root)
            runtime = self.make_runtime(root, corpus, impl)
            blocked_cache = root / "not-a-directory"
            blocked_cache.write_text("blocked", encoding="utf-8")
            proc = subprocess.run(
                [str(runtime / "search.sh"), "fixture", "--json"],
                text=True,
                capture_output=True,
                env=self.base_env(blocked_cache),
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["corpus"], str(corpus))
            self.assertIn("SESSION_SEARCH_LOCAL_PROJECTION DEGRADED", proc.stderr)
            self.assertNotIn("DEGRADED", proc.stdout)


if __name__ == "__main__":
    unittest.main()
