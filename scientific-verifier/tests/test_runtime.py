import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimeContractTests(unittest.TestCase):
    def test_runtime_contract_files_exist(self):
        self.assertTrue((ROOT / "runtime/python.env").is_file())
        self.assertTrue((ROOT / "runtime/requirements.in").is_file())
        self.assertTrue((ROOT / "runtime/requirements.lock").is_file())
        self.assertTrue((ROOT / "scripts/install-runtime.sh").is_file())
        self.assertTrue((ROOT / "scripts/ensure-runtime.sh").is_file())

    def test_requirements_in_has_only_direct_scientific_dependencies(self):
        requirements_in = ROOT / "runtime/requirements.in"
        self.assertTrue(requirements_in.is_file(), "requirements.in must exist")
        rows = [
            line.strip().lower()
            for line in requirements_in.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(rows, ["numpy", "networkx", "sympy", "scipy"])

    def test_lock_is_hash_pinned(self):
        requirements_lock = ROOT / "runtime/requirements.lock"
        self.assertTrue(requirements_lock.is_file(), "requirements.lock must exist")
        text = requirements_lock.read_text()
        self.assertIn("==", text)
        self.assertIn("--hash=sha256:", text)
        for name in ("numpy", "networkx", "sympy", "scipy"):
            self.assertIn(f"{name}==", text.lower())
