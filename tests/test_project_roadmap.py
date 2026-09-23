from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "project-roadmap" / "roadmap.py"
CONFIG = ROOT / "config" / "project-roadmap.json"
FIXTURES = ROOT / "tests" / "fixtures" / "project-roadmap"

SPEC = importlib.util.spec_from_file_location("project_roadmap", MODULE_PATH)
assert SPEC and SPEC.loader
roadmap = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = roadmap
SPEC.loader.exec_module(roadmap)


class ProjectRoadmapVerifierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = roadmap.load_config(CONFIG)

    def load(self, name: str):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def codes(self, receipt):
        return [item["code"] for item in receipt["findings"]]

    def test_pass_fixture(self):
        receipt = roadmap.verify_snapshot(self.load("pass.json"), self.config)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["findings"], [])

    def test_closed_in_progress_is_drift(self):
        receipt = roadmap.verify_snapshot(
            self.load("closed-in-progress.json"), self.config
        )
        self.assertEqual(receipt["status"], "DRIFT")
        self.assertIn("TERMINAL_ENTITY_IN_PROGRESS", self.codes(receipt))

    def test_migration_without_receipt_is_drift(self):
        receipt = roadmap.verify_snapshot(
            self.load("migration-missing-receipt.json"), self.config
        )
        self.assertEqual(receipt["status"], "DRIFT")
        self.assertIn("MIGRATION_RECEIPT_MISSING", self.codes(receipt))

    def test_connection_incomplete_is_drift(self):
        receipt = roadmap.verify_snapshot(
            self.load("connection-incomplete.json"), self.config
        )
        self.assertEqual(receipt["status"], "DRIFT")
        self.assertIn("PROJECT_CONNECTION_MISSING_ITEM", self.codes(receipt))

    def test_explicit_markers_are_deterministic(self):
        markers = roadmap.extract_markers(
            "Parent: #48\nDisposition: MIGRATED\n"
            "Migration-Receipt: https://github.com/example/repo/issues/1\n"
            "Owner-Issue: #54\n"
        )
        self.assertEqual(markers["parent_issue"], 48)
        self.assertEqual(markers["disposition"], "MIGRATED")
        self.assertEqual(
            markers["migration_receipt_url"],
            "https://github.com/example/repo/issues/1",
        )
        self.assertEqual(markers["owner_issue"], 54)

    def test_snapshot_fixture_contains_no_body_text(self):
        snapshot = self.load("pass.json")
        for entity in snapshot["entities"]:
            self.assertNotIn("body", entity)

    def test_verify_cli_exit_codes(self):
        for name, expected in (("pass.json", 0), ("connection-incomplete.json", 1)):
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--config",
                    str(CONFIG),
                    "verify",
                    str(FIXTURES / name),
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(proc.returncode, expected, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "PASS" if expected == 0 else "DRIFT")


if __name__ == "__main__":
    unittest.main()
