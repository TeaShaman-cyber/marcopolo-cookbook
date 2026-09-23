import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATERIALIZE = ROOT / "materialize-runtime.sh"


class SessionSearchStatusTests(unittest.TestCase):
    def make_implementation(self, root: pathlib.Path) -> tuple[pathlib.Path, str]:
        impl = root / "impl"
        (impl / "session_search").mkdir(parents=True)
        (impl / "session_search" / "search.py").write_text(
            "# search implementation\n", encoding="utf-8"
        )
        subprocess.run(["git", "init", "-q", "-b", "main", str(impl)], check=True)
        subprocess.run(
            ["git", "-C", str(impl), "add", "session_search/search.py"], check=True
        )
        env = os.environ.copy()
        env.update(
            {"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid"}
        )
        env.update(
            {
                "GIT_COMMITTER_NAME": "test",
                "GIT_COMMITTER_EMAIL": "test@example.invalid",
            }
        )
        subprocess.run(
            ["git", "-C", str(impl), "commit", "-q", "-m", "fixture"],
            check=True,
            env=env,
        )
        head = subprocess.check_output(
            ["git", "-C", str(impl), "rev-parse", "HEAD"], text=True
        ).strip()
        return impl, head

    def make_corpus(self, root: pathlib.Path) -> pathlib.Path:
        corpus = root / "corpus"
        (corpus / "ledger" / "accepted").mkdir(parents=True)
        (corpus / "corpus.sqlite3").write_bytes(b"projection")
        (corpus / "ledger" / "accepted" / "a.json").write_text("{}\n", encoding="utf-8")
        return corpus

    def make_runtime(self, root: pathlib.Path) -> pathlib.Path:
        runtime = root / "runtime"
        subprocess.run(
            [str(MATERIALIZE), str(runtime)], check=True, capture_output=True, text=True
        )
        return runtime

    def run_status(
        self,
        runtime: pathlib.Path,
        impl: pathlib.Path,
        corpus: pathlib.Path,
        **extra: str,
    ):
        env = os.environ.copy()
        env.update(
            {
                "SESSION_SEARCH_CANONICAL_DIR": str(ROOT),
                "SESSION_SEARCH_IMPLEMENTATION_ROOT": str(impl),
                "SESSION_SEARCH_CORPUS": str(corpus),
            }
        )
        env.update(extra)
        proc = subprocess.run(
            [str(runtime / "status.sh"), "--json"],
            text=True,
            capture_output=True,
            env=env,
        )
        payload = json.loads(proc.stdout)
        return proc, payload

    def test_ready_status_binds_runtime_implementation_and_corpus(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            runtime = self.make_runtime(root)
            impl, head = self.make_implementation(root)
            corpus = self.make_corpus(root)
            proc, payload = self.run_status(
                runtime, impl, corpus, SESSION_SEARCH_IMPLEMENTATION_HEAD=head
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(payload["local_state"], "READY")
            self.assertEqual(payload["runtime_projection"]["state"], "MATCH")
            self.assertEqual(payload["implementation"]["state"], "BOUND")
            self.assertEqual(payload["corpus"]["state"], "BOUND")
            self.assertEqual(payload["corpus"]["integrity"], "NOT_CHECKED")
            self.assertEqual(
                payload["implementation"]["remote_currentness"], "NOT_CHECKED"
            )

    def test_stale_runtime_projection_blocks_search_safety(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            runtime = self.make_runtime(root)
            impl, _head = self.make_implementation(root)
            corpus = self.make_corpus(root)
            (runtime / "search.sh").write_text(
                (runtime / "search.sh").read_text() + "\n# drift\n"
            )
            proc, payload = self.run_status(runtime, impl, corpus)
            self.assertEqual(proc.returncode, 69)
            self.assertEqual(payload["runtime_projection"]["state"], "STALE")
            self.assertIn("runtime_projection", payload["blockers"])

    def test_dirty_session_search_implementation_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            runtime = self.make_runtime(root)
            impl, _head = self.make_implementation(root)
            corpus = self.make_corpus(root)
            (impl / "session_search" / "search.py").write_text(
                "# changed\n", encoding="utf-8"
            )
            proc, payload = self.run_status(runtime, impl, corpus)
            self.assertEqual(proc.returncode, 69)
            self.assertEqual(payload["implementation"]["state"], "DIRTY")
            self.assertIn("implementation", payload["blockers"])

    def test_missing_corpus_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            runtime = self.make_runtime(root)
            impl, _head = self.make_implementation(root)
            corpus = root / "missing"
            proc, payload = self.run_status(runtime, impl, corpus)
            self.assertEqual(proc.returncode, 69)
            self.assertEqual(payload["corpus"]["state"], "UNAVAILABLE")
            self.assertIn("corpus", payload["blockers"])

    def test_observed_corpus_token_changes_when_accepted_set_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            runtime = self.make_runtime(root)
            impl, _head = self.make_implementation(root)
            corpus = self.make_corpus(root)
            first_proc, first = self.run_status(runtime, impl, corpus)
            self.assertEqual(first_proc.returncode, 0)
            (corpus / "ledger" / "accepted" / "b.json").write_text(
                "{}\n", encoding="utf-8"
            )
            second_proc, second = self.run_status(runtime, impl, corpus)
            self.assertEqual(second_proc.returncode, 0)
            self.assertNotEqual(
                first["corpus"]["observed_generation"],
                second["corpus"]["observed_generation"],
            )
            self.assertEqual(second["corpus"]["accepted_count"], 2)

    def test_explicit_environment_wins_while_runtime_env_fills_missing_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            runtime = self.make_runtime(root)
            impl, _head = self.make_implementation(root)
            bound_corpus = self.make_corpus(root / "bound")
            override_corpus = self.make_corpus(root / "override")
            (runtime / "runtime.env").write_text(
                f"SESSION_SEARCH_CORPUS={bound_corpus}\n"
                f"SESSION_SEARCH_IMPLEMENTATION_ROOT={impl}\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env.update(
                {
                    "SESSION_SEARCH_CANONICAL_DIR": str(ROOT),
                    "SESSION_SEARCH_CORPUS": str(override_corpus),
                }
            )
            proc = subprocess.run(
                [str(runtime / "status.sh"), "--json"],
                text=True,
                capture_output=True,
                env=env,
            )
            payload = json.loads(proc.stdout)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(payload["corpus"]["root"], str(override_corpus))
            self.assertEqual(payload["implementation"]["root"], str(impl))

    def test_expected_head_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            runtime = self.make_runtime(root)
            impl, _head = self.make_implementation(root)
            corpus = self.make_corpus(root)
            proc, payload = self.run_status(
                runtime, impl, corpus, SESSION_SEARCH_IMPLEMENTATION_HEAD="0" * 40
            )
            self.assertEqual(proc.returncode, 69)
            self.assertEqual(payload["implementation"]["state"], "STALE")
            self.assertEqual(payload["implementation"]["reason"], "head_mismatch")

    def test_acceptance_uses_same_freshness_gate_as_search(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            runtime = self.make_runtime(root)
            impl, _head = self.make_implementation(root)
            corpus = self.make_corpus(root)
            (runtime / "runtime.env").write_text(
                f"SESSION_SEARCH_CORPUS={corpus}\n"
                f"SESSION_SEARCH_IMPLEMENTATION_ROOT={impl}\n"
                f"SESSION_SEARCH_IMPLEMENTATION_HEAD={'0' * 40}\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["SESSION_SEARCH_CANONICAL_DIR"] = str(ROOT)
            proc = subprocess.run(
                [str(runtime / "acceptance.sh"), "--query", "fixture"],
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertEqual(proc.returncode, 69)
            self.assertIn("LOCAL_FRESHNESS_CHECK_FAILED", proc.stderr)
            self.assertNotIn("SESSION_SEARCH_ACCEPTANCE mode=", proc.stdout)

    def test_explicit_canonical_dir_wins_over_runtime_env_and_exposes_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            runtime = self.make_runtime(root)
            impl, _head = self.make_implementation(root)
            corpus = self.make_corpus(root)
            (runtime / "runtime.env").write_text(
                f"SESSION_SEARCH_CORPUS={corpus}\n"
                f"SESSION_SEARCH_IMPLEMENTATION_ROOT={impl}\n"
                f"SESSION_SEARCH_CANONICAL_DIR={runtime}\n",
                encoding="utf-8",
            )
            (runtime / "search.sh").write_text(
                (runtime / "search.sh").read_text(encoding="utf-8") + "\n# drift\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["SESSION_SEARCH_CANONICAL_DIR"] = str(ROOT)
            proc = subprocess.run(
                [str(runtime / "status.sh"), "--json"],
                text=True,
                capture_output=True,
                env=env,
            )
            payload = json.loads(proc.stdout)
            self.assertEqual(proc.returncode, 69)
            self.assertEqual(payload["runtime_projection"]["state"], "STALE")
            self.assertIn("runtime_projection", payload["blockers"])

    def test_untracked_implementation_is_dirty_even_when_git_config_hides_untracked(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            runtime = self.make_runtime(root)
            impl = root / "impl"
            impl.mkdir()
            (impl / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", "-b", "main", str(impl)], check=True)
            subprocess.run(["git", "-C", str(impl), "add", "README.md"], check=True)
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
            subprocess.run(
                ["git", "-C", str(impl), "config", "status.showUntrackedFiles", "no"],
                check=True,
            )
            (impl / "session_search").mkdir()
            (impl / "session_search" / "search.py").write_text(
                "# untracked\n", encoding="utf-8"
            )
            corpus = self.make_corpus(root)
            proc, payload = self.run_status(runtime, impl, corpus)
            self.assertEqual(proc.returncode, 69)
            self.assertEqual(payload["implementation"]["state"], "DIRTY")
            self.assertEqual(
                payload["implementation"]["reason"], "session_search_tree_dirty"
            )
            self.assertIn("implementation", payload["blockers"])

    def test_git_status_failure_is_unknown_not_clean(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            runtime = self.make_runtime(root)
            impl, _head = self.make_implementation(root)
            corpus = self.make_corpus(root)
            (impl / ".git" / "index").write_bytes(b"broken-index")
            proc, payload = self.run_status(runtime, impl, corpus)
            self.assertEqual(proc.returncode, 69)
            self.assertEqual(payload["implementation"]["state"], "UNKNOWN")
            self.assertEqual(
                payload["implementation"]["reason"], "git_status_unavailable"
            )
            self.assertIn("implementation", payload["blockers"])


if __name__ == "__main__":
    unittest.main()
