#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS="$ROOT/requirements-python.txt"
PYTHON_BIN="${PYTHON_BIN:-python3}"

check_runtime() {
  "$PYTHON_BIN" - <<'PY'
import importlib.metadata as metadata

required = {
    "attrs": "26.1.0",
    "jsonschema": "4.26.0",
    "jsonschema-specifications": "2025.9.1",
    "referencing": "0.37.0",
    "rpds-py": "2026.6.3",
    "typing_extensions": "4.16.0",
}

for package, expected in required.items():
    actual = metadata.version(package)
    if actual != expected:
        raise SystemExit(f"{package}: expected {expected}, found {actual}")

import jsonschema  # noqa: F401
import referencing  # noqa: F401
print("PYTHON_RUNTIME_VERIFIED")
PY
}

if [[ "${1:-}" == "--check" ]]; then
  check_runtime
  exit 0
fi

if check_runtime >/dev/null 2>&1; then
  echo "PYTHON_RUNTIME_ALREADY_VERIFIED"
  exit 0
fi

"$PYTHON_BIN" -m pip install \
  --user \
  --disable-pip-version-check \
  --no-warn-script-location \
  -r "$REQUIREMENTS"

check_runtime
