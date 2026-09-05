#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash -n "$ROOT/marcopolo/bootstrap-python.sh"
test -f "$ROOT/marcopolo/requirements-python.txt"
grep -Fx 'jsonschema==4.26.0' "$ROOT/marcopolo/requirements-python.txt" >/dev/null
grep -Fx 'referencing==0.37.0' "$ROOT/marcopolo/requirements-python.txt" >/dev/null
"$ROOT/marcopolo/bootstrap-python.sh" --check
