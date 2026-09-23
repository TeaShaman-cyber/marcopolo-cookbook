import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATERIALIZE = ROOT / "materialize-runtime.sh"
FILES = (
    "README.md",
    "search.sh",
    "acceptance.sh",
    "status.sh",
    "status.py",
    "runtime-bindings.sh",
    "local-projection.sh",
    "local_projection.py",
)


class SessionSearchRuntimeMaterializerTests(unittest.TestCase):
    def test_materializer_preserves_runtime_binding_and_projects_tracked_helpers(self):
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "runtime"
            target.mkdir()
            binding = target / "runtime.env"
            binding.write_text(
                "SESSION_SEARCH_CORPUS=/private/example\n", encoding="utf-8"
            )
            original = binding.read_bytes()

            proc = subprocess.run(
                [str(MATERIALIZE), str(target)], text=True, capture_output=True
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(binding.read_bytes(), original)
            for name in FILES:
                self.assertEqual(
                    (ROOT / name).read_bytes(), (target / name).read_bytes()
                )

    def test_materializer_can_project_exact_git_ref_without_using_checkout_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "runtime"
            proc = subprocess.run(
                [str(MATERIALIZE), "--ref", "HEAD", str(target)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn(
                "SESSION_SEARCH_RUNTIME_MATERIALIZED source=HEAD@", proc.stdout
            )
            repo_root = ROOT.parent
            for name in FILES:
                expected = subprocess.check_output(
                    ["git", "-C", str(repo_root), "show", f"HEAD:session-search/{name}"]
                )
                self.assertEqual(expected, (target / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
