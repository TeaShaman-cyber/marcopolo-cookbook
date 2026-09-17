#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT/runtime/python.env"
CACHE="$("$ROOT/scripts/ensure-runtime.sh")"

case "$CACHE" in
  /tmp/marcopolo-scientific-verifier-*) ;;
  *) echo "FAIL: unexpected runtime cache path: $CACHE" >&2; exit 1 ;;
esac

PY="$CACHE/bin/python"
[[ -x "$PY" ]] || { echo "FAIL: runtime python missing" >&2; exit 1; }
[[ "$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" == "$PYTHON_VERSION" ]] || {
  echo "FAIL: Python major/minor mismatch" >&2
  exit 1
}

"$PY" - <<'PY'
import networkx
import numpy
import scipy
import sympy
print("IMPORTS=OK")
PY

RECEIPT="$("$PY" "$ROOT/scripts/runtime-receipt.py")"
SUMMARY="$("$PY" - "$RECEIPT" "$RUNTIME_BUNDLE" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
expected_bundle = sys.argv[2]
expected_keys = {"packages", "python", "runtime_bundle"}
expected_packages = {"numpy", "networkx", "sympy", "scipy"}

assert set(payload) == expected_keys, payload
assert payload["python"].startswith("3.11."), payload
assert payload["runtime_bundle"] == expected_bundle, payload
assert set(payload["packages"]) == expected_packages, payload
assert all(payload["packages"].values()), payload

p = payload["packages"]
print(
    f"bundle={payload['runtime_bundle']} "
    f"python={payload['python']} "
    f"numpy={p['numpy']} networkx={p['networkx']} "
    f"sympy={p['sympy']} scipy={p['scipy']}"
)
PY
)"
printf "PASS scientific-verifier-runtime %s\n" "$SUMMARY"
