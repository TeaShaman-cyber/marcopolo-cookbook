from __future__ import annotations

import base64
import binascii
import hmac
import json
import os
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


_ALLOWED_RECEIPT_FIELDS = {
    "listener_ready",
    "json_to_script",
    "basic_received",
    "mcporter_called",
    "bearer_matches_basic",
}


@dataclass
class PilotState:
    listener_ready: bool = False
    json_to_script: bool = False
    basic_received: bool = False
    mcporter_called: bool = False
    bearer_matches_basic: bool = False
    username: str | None = None
    password: str | None = None


def parse_basic_header(value: str) -> tuple[str, str]:
    scheme, sep, encoded = value.partition(" ")
    if scheme != "Basic" or not sep or not encoded:
        raise ValueError("BASIC_MISSING_OR_MALFORMED")

    try:
        raw = base64.b64decode(encoded, validate=True).decode("latin-1")
    except (binascii.Error, UnicodeDecodeError):
        raise ValueError("BASIC_MISSING_OR_MALFORMED") from None

    username, sep, password = raw.partition(":")
    if not sep:
        raise ValueError("BASIC_MISSING_OR_MALFORMED")
    return username, password


def build_mcporter_argv(config_path: str) -> tuple[str, ...]:
    return (
        "/workspace/tools/mcporter/bin/mcporter",
        "--config",
        config_path,
        "call",
        "pilot.probe",
    )


def safe_receipt(state: dict[str, bool]) -> dict[str, bool]:
    if not set(state).issubset(_ALLOWED_RECEIPT_FIELDS):
        raise ValueError("UNSAFE_RECEIPT_FIELD")
    if any(type(value) is not bool for value in state.values()):
        raise ValueError("UNSAFE_RECEIPT_VALUE")
    return dict(state)


def write_ready_marker(
    run_nonce: str,
    root: Path = Path("/workspace/artifacts/json-secret-env-pilot"),
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    marker = root / f"ready-{run_nonce}"
    temporary = root / f".ready-{run_nonce}.{os.getpid()}.tmp"
    temporary.write_text("READY", encoding="ascii")
    os.replace(temporary, marker)
    return marker


class PilotRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    @property
    def state(self) -> PilotState:
        return self.server.pilot_state  # type: ignore[attr-defined]

    def _empty(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _json(self, status: int, payload: dict[str, object]) -> None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        if self.path == "/ingest":
            self._handle_ingest()
            return
        if self.path == "/mcp":
            self._handle_mcp()
            return
        self._empty(404)

    def _handle_ingest(self) -> None:
        if self.state.basic_received:
            self._empty(409)
            return

        try:
            username, password = parse_basic_header(self.headers.get("Authorization", ""))
        except ValueError:
            self._empty(401)
            return

        self.state.username = username
        self.state.password = password
        self.state.basic_received = True
        self.state.json_to_script = True
        self._empty(204)

    def _handle_mcp(self) -> None:
        if not self.state.basic_received or self.state.password is None:
            self._empty(409)
            return

        expected = f"Bearer {self.state.password}"
        observed = self.headers.get("Authorization", "")
        if not hmac.compare_digest(observed, expected):
            self._empty(401)
            return

        self.state.mcporter_called = True
        self.state.bearer_matches_basic = True

        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length) if length else b"{}")
        except (ValueError, json.JSONDecodeError):
            self._empty(400)
            return

        method = request.get("method")
        request_id = request.get("id")

        if method == "notifications/initialized":
            self._empty(202)
            return

        if method == "initialize":
            result: dict[str, object] = {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "pilot", "version": "0.1"},
            }
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "probe",
                        "description": "Synthetic transport probe",
                        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
                    }
                ]
            }
        elif method == "tools/call" and request.get("params", {}).get("name") == "probe":
            result = {"content": [{"type": "text", "text": "ok"}], "isError": False}
        else:
            self._json(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": "Method not found"},
                },
            )
            return

        self._json(200, {"jsonrpc": "2.0", "id": request_id, "result": result})


def create_server(
    state: PilotState,
    host: str = "0.0.0.0",
    port: int = 18765,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), PilotRequestHandler)
    server.pilot_state = state  # type: ignore[attr-defined]
    state.listener_ready = True
    return server
