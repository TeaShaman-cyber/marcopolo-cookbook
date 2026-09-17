#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT/runtime/python.env"
LOCK="$ROOT/runtime/requirements.lock"
CACHE_ROOT="${TMPDIR:-/tmp}/marcopolo-scientific-verifier-$(id -u)"
CACHE="$CACHE_ROOT/$RUNTIME_BUNDLE"
RECEIPT=.scientific-verifier-runtime.json

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

[[ -L "$CACHE_ROOT" ]] && fail "cache root is a symlink: $CACHE_ROOT"
if [[ -e "$CACHE_ROOT" && ! -d "$CACHE_ROOT" ]]; then
  fail "cache root is not a directory: $CACHE_ROOT"
fi
mkdir -p "$CACHE_ROOT"
chmod 700 "$CACHE_ROOT"
[[ "$(stat -c %u "$CACHE_ROOT")" == "$(id -u)" ]] || fail "cache root ownership mismatch"

HOST_PYTHON="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
[[ "$HOST_PYTHON" == "$PYTHON_VERSION" ]] || fail "host python $HOST_PYTHON != required $PYTHON_VERSION"
[[ -f "$LOCK" ]] || fail "missing requirements lock: $LOCK"

STAGE="$(mktemp -d "$CACHE_ROOT/.build-${RUNTIME_BUNDLE}-XXXXXX")"
OLD=""
cleanup() {
  rm -rf "$STAGE"
  if [[ -n "$OLD" && -e "$OLD" && ! -e "$CACHE" ]]; then
    mv "$OLD" "$CACHE"
  fi
}
trap cleanup EXIT

python3 -m venv "$STAGE"
PIP_DISABLE_PIP_VERSION_CHECK=1 "$STAGE/bin/python" -m pip install --require-hashes -r "$LOCK" >/dev/null

"$STAGE/bin/python" - "$LOCK" "$RUNTIME_BUNDLE" "$RECEIPT" <<'PY'
import importlib.metadata as metadata
import json
from pathlib import Path
import re
import sys

lock_path = Path(sys.argv[1])
bundle = sys.argv[2]
receipt_name = sys.argv[3]
direct = ("numpy", "networkx", "sympy", "scipy")

expected = {}
pattern = re.compile(r"^(numpy|networkx|sympy|scipy)==([^\\\s]+)", re.I)
for line in lock_path.read_text().splitlines():
    match = pattern.match(line.strip())
    if match:
        expected[match.group(1).lower()] = match.group(2)

if set(expected) != set(direct):
    raise SystemExit(f"lock direct-package set mismatch: {sorted(expected)}")

import networkx  # noqa: F401
import numpy  # noqa: F401
import scipy  # noqa: F401
import sympy  # noqa: F401

actual = {name: metadata.version(name) for name in direct}
if actual != expected:
    raise SystemExit(f"package version mismatch: expected={expected} actual={actual}")

receipt = {
    "packages": actual,
    "python": ".".join(map(str, sys.version_info[:3])),
    "runtime_bundle": bundle,
}
(Path(sys.prefix) / receipt_name).write_text(
    json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n"
)
PY

if [[ -e "$CACHE" || -L "$CACHE" ]]; then
  OLD="$CACHE_ROOT/.old-${RUNTIME_BUNDLE}-$$"
  rm -rf "$OLD"
  mv "$CACHE" "$OLD"
fi
mv "$STAGE" "$CACHE"
STAGE=""
if [[ -n "$OLD" ]]; then
  rm -rf "$OLD"
  OLD=""
fi
trap - EXIT
printf '%s\n' "$CACHE"
