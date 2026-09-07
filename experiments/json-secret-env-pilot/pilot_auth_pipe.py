from __future__ import annotations

import base64
import binascii


_ALLOWED_RECEIPT_FIELDS = {
    "listener_ready",
    "json_to_script",
    "basic_received",
    "mcporter_called",
    "bearer_matches_basic",
}


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
