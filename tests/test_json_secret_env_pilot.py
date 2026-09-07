import base64
import sys
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1] / "experiments" / "json-secret-env-pilot"
sys.path.insert(0, str(MODULE_DIR))

from pilot_auth_pipe import build_mcporter_argv, parse_basic_header, safe_receipt


class BasicHeaderTests(unittest.TestCase):
    def test_parse_basic_header(self):
        payload = base64.b64encode(b"pilot-user:synthetic-value").decode("ascii")
        self.assertEqual(
            parse_basic_header(f"Basic {payload}"),
            ("pilot-user", "synthetic-value"),
        )

    def test_rejects_non_basic_header(self):
        with self.assertRaisesRegex(ValueError, "BASIC_MISSING_OR_MALFORMED"):
            parse_basic_header("Bearer synthetic-value")

    def test_rejects_invalid_base64(self):
        with self.assertRaisesRegex(ValueError, "BASIC_MISSING_OR_MALFORMED"):
            parse_basic_header("Basic !!!")


class ProcessContractTests(unittest.TestCase):
    def test_mcporter_argv_is_fixed_and_value_free(self):
        config_path = "/workspace/pilot/mcporter.json"
        argv = build_mcporter_argv(config_path)
        self.assertEqual(
            argv,
            (
                "/workspace/tools/mcporter/bin/mcporter",
                "--config",
                config_path,
                "call",
                "pilot.probe",
            ),
        )
        self.assertNotIn("synthetic-value", " ".join(argv))

    def test_safe_receipt_accepts_only_approved_booleans(self):
        receipt = safe_receipt(
            {
                "listener_ready": True,
                "json_to_script": True,
                "basic_received": True,
                "mcporter_called": False,
                "bearer_matches_basic": False,
            }
        )
        self.assertEqual(receipt["listener_ready"], True)
        self.assertEqual(receipt["mcporter_called"], False)

    def test_safe_receipt_rejects_unknown_fields(self):
        with self.assertRaises(ValueError):
            safe_receipt({"listener_ready": True, "runtime_value": True})

    def test_safe_receipt_rejects_non_boolean_values(self):
        with self.assertRaises(ValueError):
            safe_receipt({"listener_ready": "yes"})


if __name__ == "__main__":
    unittest.main()
