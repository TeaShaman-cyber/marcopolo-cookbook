from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol

CORE_SCHEMA_VERSION = "memory-core-v0.1"
LIFECYCLE_STATES = {"OBSERVED", "CANDIDATE", "PENDING", "SUPERSEDED", "TOMBSTONED"}

SENSITIVE_FIELD_NAMES = {
    "api_key",
    "apikey",
    "password",
    "passwd",
    "token",
    "access_token",
    "refresh_token",
    "client_secret",
    "authorization",
    "cookie",
    "private_key",
    "credential",
    "credentials",
    "secret",
}


class MemoryAdapterError(RuntimeError):
    pass


class AuthorizationError(MemoryAdapterError):
    pass


class AdmissionError(MemoryAdapterError):
    pass


class AdapterDisabled(MemoryAdapterError):
    pass


class Runner(Protocol):
    def run(self, query_name: str, params: Mapping[str, Any]) -> dict[str, Any]: ...


class RecordingRunner:
    def __init__(self, delegate: Runner) -> None:
        self.delegate = delegate
        self.trace: list[dict[str, Any]] = []

    def run(self, query_name: str, params: Mapping[str, Any]) -> dict[str, Any]:
        result = self.delegate.run(query_name, params)
        self.trace.append(
            {
                "sequence": len(self.trace) + 1,
                "query_name": query_name,
                "param_names": sorted(params),
                "result_status": result.get("status")
                or result.get("result_state")
                or "OK",
            }
        )
        return result


class ConnectionQueryRunner:
    QUERY_FILES = {
        "bootstrap": "00_bootstrap.sql",
        "retain": "10_retain.sql",
        "readback": "20_readback.sql",
        "recall": "30_recall.sql",
        "reconcile": "40_reconcile.sql",
    }

    def __init__(
        self,
        *,
        connection_name: str,
        query_dir: str | Path,
        timeout_seconds: int = 20,
        executable: str = "connection",
    ) -> None:
        self.connection_name = connection_name
        self.query_dir = Path(query_dir).resolve()
        self.timeout_seconds = timeout_seconds
        self.executable = executable

    @staticmethod
    def _json_object(value: Any, field: str) -> dict[str, Any]:
        if value is None:
            raise MemoryAdapterError(f"QUERY_RESULT_MISSING:{field}")
        try:
            parsed = json.loads(value) if isinstance(value, str) else value
        except (TypeError, json.JSONDecodeError) as exc:
            raise MemoryAdapterError(f"QUERY_RESULT_JSON_INVALID:{field}") from exc
        if not isinstance(parsed, dict):
            raise MemoryAdapterError(f"QUERY_RESULT_JSON_INVALID:{field}")
        return parsed

    def run(self, query_name: str, params: Mapping[str, Any]) -> dict[str, Any]:
        filename = self.QUERY_FILES.get(query_name)
        if filename is None:
            raise MemoryAdapterError("QUERY_NAME_INVALID")
        query_path = self.query_dir / filename
        if not query_path.is_file():
            raise MemoryAdapterError("QUERY_FILE_MISSING")

        command = [
            self.executable,
            "query",
            self.connection_name,
            "--file",
            str(query_path),
            "--params-json",
            json.dumps(dict(params), sort_keys=True, separators=(",", ":")),
            "--include-results",
            "--json",
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MemoryAdapterError("QUERY_TRANSPORT_FAILED") from exc
        if completed.returncode != 0:
            raise MemoryAdapterError("QUERY_EXECUTION_FAILED")

        try:
            envelope = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise MemoryAdapterError("QUERY_ENVELOPE_INVALID") from exc
        if not isinstance(envelope, dict) or envelope.get("success") is not True:
            raise MemoryAdapterError("QUERY_ENVELOPE_FAILED")

        data = envelope.get("data")
        try:
            rows = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError as exc:
            raise MemoryAdapterError("QUERY_DATA_INVALID") from exc
        if not isinstance(rows, list):
            raise MemoryAdapterError("QUERY_DATA_INVALID")
        if (
            envelope.get("row_count") != 1
            or len(rows) != 1
            or not isinstance(rows[0], dict)
        ):
            raise MemoryAdapterError("QUERY_RESULT_CARDINALITY")
        row = dict(rows[0])

        if query_name == "retain":
            receipt_json = row.pop("stored_receipt_json", None)
            row["stored_receipt"] = (
                None
                if receipt_json is None
                else self._json_object(receipt_json, "stored_receipt_json")
            )
            return row
        if query_name == "recall":
            if row.get("status") != "OK":
                return {"status": row.get("status", "QUERY_RESULT_STATUS_INVALID")}
            return self._json_object(row.get("packet_json"), "packet_json")
        if query_name == "readback":
            if row.get("status") != "HIT":
                return {"status": row.get("status", "MISS_UNKNOWN")}
            return self._json_object(row.get("stored_event_json"), "stored_event_json")
        if query_name == "reconcile":
            if row.get("status") != "OK":
                return {"status": row.get("status", "QUERY_RESULT_STATUS_INVALID")}
            return self._json_object(row.get("reconcile_json"), "reconcile_json")
        return row


@dataclass(frozen=True)
class TrustedExecutionContext:
    trusted_principal_id: str


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def hex_transport(value: str | bytes) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8")
    return raw.hex()


def contains_structured_credential(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in SENSITIVE_FIELD_NAMES and child not in (None, "", [], {}):
                return True
            if contains_structured_credential(child):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(contains_structured_credential(child) for child in value)
    return False


def _encode_cursor(created_at: str, event_id: str) -> str:
    raw = f"{created_at}\n{event_id}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[str, str]:
    if not cursor or any(
        ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        for ch in cursor
    ):
        raise AdmissionError("INVALID_CURSOR")
    padding = "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(cursor + padding).decode("utf-8")
        created_at, event_id = raw.split("\n", 1)
    except Exception as exc:
        raise AdmissionError("INVALID_CURSOR") from exc
    if not created_at or not event_id:
        raise AdmissionError("INVALID_CURSOR")
    return created_at, event_id


class MemoryAdapter:
    def __init__(
        self,
        *,
        runner: Runner,
        authorization: Mapping[str, Any],
        enabled: bool = True,
        synthetic_only: bool = False,
        max_event_bytes: int = 8192,
    ) -> None:
        self.runner = runner
        self.authorization = dict(authorization)
        self.enabled = enabled
        self.synthetic_only = synthetic_only
        self.max_event_bytes = max_event_bytes

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise AdapterDisabled("ADAPTER_DISABLED")

    def _effective_scope(
        self, context: TrustedExecutionContext, requested_scope: str
    ) -> str:
        self._require_enabled()
        principals = self.authorization.get("principals", {})
        principal = principals.get(context.trusted_principal_id)
        if principal is None:
            raise AuthorizationError("AUTHZ_PRINCIPAL_UNKNOWN")
        allowed = principal.get("allowed_scopes", [])
        if requested_scope not in allowed:
            raise AuthorizationError("AUTHZ_SCOPE_DENIED")
        return requested_scope

    def _admit_event(self, effective_scope: str, event: Mapping[str, Any]) -> bytes:
        required = {
            "event_id",
            "scope",
            "source_class",
            "lifecycle_state",
            "created_at",
            "provenance",
            "payload",
        }
        missing = sorted(required.difference(event))
        if missing:
            raise AdmissionError("EVENT_SCHEMA_INVALID:" + ",".join(missing))
        if event["scope"] != effective_scope:
            raise AuthorizationError("AUTHZ_SCOPE_DENIED")
        if event["lifecycle_state"] not in LIFECYCLE_STATES:
            raise AdmissionError("LIFECYCLE_INVALID")
        created_at = event["created_at"]
        if not isinstance(created_at, str):
            raise AdmissionError("CREATED_AT_INVALID")
        try:
            parsed_created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            raise AdmissionError("CREATED_AT_INVALID") from exc
        if parsed_created_at.strftime("%Y-%m-%dT%H:%M:%SZ") != created_at:
            raise AdmissionError("CREATED_AT_INVALID")
        if contains_structured_credential(
            event["payload"]
        ) or contains_structured_credential(event["provenance"]):
            raise AdmissionError("CREDENTIAL_MATERIAL_REJECTED")
        if not isinstance(event["provenance"], Mapping) or not event["provenance"].get(
            "source_ref"
        ):
            raise AdmissionError("PROVENANCE_INVALID")
        if self.synthetic_only and event["source_class"] != "synthetic":
            raise AdmissionError("SPIKE_SYNTHETIC_ONLY")

        canonical = canonical_json_bytes(dict(event))
        if len(canonical) > self.max_event_bytes:
            raise AdmissionError("EVENT_TOO_LARGE")
        return canonical

    def retain(
        self,
        context: TrustedExecutionContext,
        operation_id: str,
        event: Mapping[str, Any],
    ) -> dict[str, Any]:
        effective_scope = self._effective_scope(context, str(event.get("scope", "")))
        canonical_event = self._admit_event(effective_scope, event)
        canonical_request = canonical_json_bytes(
            {
                "operation_id": operation_id,
                "event": json.loads(canonical_event.decode("utf-8")),
            }
        )
        request_fingerprint = hashlib.sha256(canonical_request).hexdigest()

        params = {
            "operation_id_hex": hex_transport(operation_id),
            "request_fingerprint_hex": hex_transport(request_fingerprint),
            "event_id_hex": hex_transport(str(event["event_id"])),
            "scope_hex": hex_transport(effective_scope),
            "source_class_hex": hex_transport(str(event["source_class"])),
            "lifecycle_state_hex": hex_transport(str(event["lifecycle_state"])),
            "created_at_hex": hex_transport(str(event["created_at"])),
            "provenance_json_hex": hex_transport(
                canonical_json_bytes(event["provenance"])
            ),
            "payload_json_hex": hex_transport(canonical_json_bytes(event["payload"])),
        }
        return self.runner.run("retain", params)

    def recall(
        self,
        context: TrustedExecutionContext,
        *,
        scope: str,
        filters: Mapping[str, Any],
        limit: int = 20,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        effective_scope = self._effective_scope(context, scope)
        if not isinstance(limit, int) or not 1 <= limit <= 100:
            raise AdmissionError("LIMIT_INVALID")
        allowed_filters = {
            "event_id",
            "operation_id",
            "source_class",
            "lifecycle",
            "created_after",
            "created_before",
        }
        unknown = sorted(set(filters).difference(allowed_filters))
        if unknown:
            raise AdmissionError("FILTER_UNSUPPORTED:" + ",".join(unknown))

        lifecycle = filters.get("lifecycle") or []
        if not isinstance(lifecycle, list) or any(
            state not in LIFECYCLE_STATES for state in lifecycle
        ):
            raise AdmissionError("LIFECYCLE_FILTER_INVALID")

        cursor_created_at = ""
        cursor_event_id = ""
        has_cursor = 0
        if cursor is not None:
            cursor_created_at, cursor_event_id = _decode_cursor(cursor)
            has_cursor = 1

        def opt_hex(name: str) -> str:
            value = filters.get(name)
            return hex_transport(str(value)) if value is not None else ""

        params = {
            "scope_hex": hex_transport(effective_scope),
            "event_id_hex": opt_hex("event_id"),
            "operation_id_hex": opt_hex("operation_id"),
            "source_class_hex": opt_hex("source_class"),
            "lifecycle_json_hex": hex_transport(canonical_json_bytes(lifecycle)),
            "created_after_hex": opt_hex("created_after"),
            "created_before_hex": opt_hex("created_before"),
            "cursor_created_at_hex": hex_transport(cursor_created_at)
            if has_cursor
            else "",
            "cursor_event_id_hex": hex_transport(cursor_event_id) if has_cursor else "",
            "has_event_id": int("event_id" in filters),
            "has_operation_id": int("operation_id" in filters),
            "has_source_class": int("source_class" in filters),
            "has_lifecycle": int(bool(lifecycle)),
            "has_created_after": int("created_after" in filters),
            "has_created_before": int("created_before" in filters),
            "has_cursor": has_cursor,
            "limit": limit,
        }
        packet = self.runner.run("recall", params)
        if packet.get("core_schema_version") not in (None, CORE_SCHEMA_VERSION):
            raise MemoryAdapterError("CORE_SCHEMA_VERSION_MISMATCH")
        return packet

    def readback(
        self,
        context: TrustedExecutionContext,
        *,
        scope: str,
        event_id: str,
    ) -> dict[str, Any]:
        effective_scope = self._effective_scope(context, scope)
        return self.runner.run(
            "readback",
            {
                "scope_hex": hex_transport(effective_scope),
                "event_id_hex": hex_transport(event_id),
            },
        )

    def reconcile(
        self,
        context: TrustedExecutionContext,
        *,
        scope: str,
    ) -> dict[str, Any]:
        effective_scope = self._effective_scope(context, scope)
        return self.runner.run(
            "reconcile", {"scope_hex": hex_transport(effective_scope)}
        )
