import base64
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1] / "experiments" / "json-secret-env-pilot"
sys.path.insert(0, str(MODULE_DIR))

from pilot_auth_pipe import (
    PilotState,
    build_mcporter_argv,
    create_server,
    parse_basic_header,
    safe_receipt,
    write_ready_marker,
)


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


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.state = PilotState()
        self.server = create_server(self.state, host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.connection = http.client.HTTPConnection(host, port, timeout=2)

    def tearDown(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _basic(self):
        payload = base64.b64encode(b"pilot-user:synthetic-value").decode("ascii")
        return f"Basic {payload}"

    def _post(self, path, body=b"", headers=None):
        headers = dict(headers or {})
        self.connection.request("POST", path, body=body, headers=headers)
        response = self.connection.getresponse()
        payload = response.read()
        return response.status, payload, dict(response.getheaders())

    def test_ingest_rejects_missing_basic(self):
        status, payload, _ = self._post("/ingest")
        self.assertEqual(status, 401)
        self.assertEqual(payload, b"")
        self.assertFalse(self.state.basic_received)

    def test_ingest_is_one_shot(self):
        status, payload, _ = self._post("/ingest", headers={"Authorization": self._basic()})
        self.assertEqual((status, payload), (204, b""))
        self.assertTrue(self.state.basic_received)
        self.assertTrue(self.state.json_to_script)

        status, payload, _ = self._post("/ingest", headers={"Authorization": self._basic()})
        self.assertEqual((status, payload), (409, b""))

    def test_mcp_before_ingest_is_rejected(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
        status, payload, _ = self._post(
            "/mcp",
            body=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer synthetic-value"},
        )
        self.assertEqual((status, payload), (409, b""))

    def test_mcp_rejects_wrong_bearer(self):
        self._post("/ingest", headers={"Authorization": self._basic()})
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
        status, payload, _ = self._post(
            "/mcp",
            body=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer wrong-value"},
        )
        self.assertEqual((status, payload), (401, b""))
        self.assertFalse(self.state.bearer_matches_basic)

    def test_probe_succeeds_with_matching_bearer(self):
        self._post("/ingest", headers={"Authorization": self._basic()})
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "probe", "arguments": {}},
            }
        ).encode()
        status, payload, _ = self._post(
            "/mcp",
            body=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer synthetic-value"},
        )
        self.assertEqual(status, 200)
        decoded = json.loads(payload)
        self.assertEqual(decoded["result"]["content"], [{"type": "text", "text": "ok"}])
        self.assertTrue(self.state.mcporter_called)
        self.assertTrue(self.state.bearer_matches_basic)
        self.assertNotIn(b"synthetic-value", payload)

    def test_ready_marker_is_atomic_and_non_sensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = write_ready_marker("abc123", root=Path(tmp))
            self.assertEqual(marker.read_text(), "READY")
            self.assertEqual(marker.name, "ready-abc123")


if __name__ == "__main__":
    unittest.main()
