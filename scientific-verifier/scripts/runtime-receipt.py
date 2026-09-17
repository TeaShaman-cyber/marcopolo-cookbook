#!/usr/bin/env python3
import importlib.metadata as metadata
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "runtime/python.env"


def load_runtime_bundle() -> str:
    values = {}
    for raw in ENV.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            raise SystemExit(f"invalid runtime env line: {raw!r}")
        values[key] = value
    bundle = values.get("RUNTIME_BUNDLE", "")
    if not bundle:
        raise SystemExit("RUNTIME_BUNDLE missing from runtime/python.env")
    return bundle


payload = {
    "packages": {
        name: metadata.version(name)
        for name in ("numpy", "networkx", "sympy", "scipy")
    },
    "python": sys.version.split()[0],
    "runtime_bundle": load_runtime_bundle(),
}
print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
