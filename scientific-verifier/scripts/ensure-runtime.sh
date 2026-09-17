#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT/runtime/python.env"
LOCK="$ROOT/runtime/requirements.lock"
CACHE_ROOT="${TMPDIR:-/tmp}/marcopolo-scientific-verifier-$(id -u)"
CACHE="$CACHE_ROOT/$RUNTIME_BUNDLE"
LOCK_FILE="$CACHE_ROOT/.${RUNTIME_BUNDLE}.lock"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

prepare_cache_root() {
  [[ -L "$CACHE_ROOT" ]] && fail "cache root is a symlink: $CACHE_ROOT"
  if [[ -e "$CACHE_ROOT" && ! -d "$CACHE_ROOT" ]]; then
    fail "cache root is not a directory: $CACHE_ROOT"
  fi
  mkdir -p "$CACHE_ROOT"
  chmod 700 "$CACHE_ROOT"
  [[ "$(stat -c %u "$CACHE_ROOT")" == "$(id -u)" ]] || fail "cache root ownership mismatch"
}

valid_cache() {
  [[ -x "$CACHE/bin/python" ]] || return 1
  [[ "$("$CACHE/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" == "$PYTHON_VERSION" ]] || return 1
  "$CACHE/bin/python" - "$LOCK" <<'PY' >/dev/null 2>&1
import importlib.metadata as metadata
from pathlib import Path
import re
import sys

lock_path = Path(sys.argv[1])
direct = ("numpy", "networkx", "sympy", "scipy")
expected = {}
pattern = re.compile(r"^(numpy|networkx|sympy|scipy)==([^\\\s]+)", re.I)
for line in lock_path.read_text().splitlines():
    match = pattern.match(line.strip())
    if match:
        expected[match.group(1).lower()] = match.group(2)
if set(expected) != set(direct):
    raise SystemExit(1)

import networkx  # noqa: F401
import numpy  # noqa: F401
import scipy  # noqa: F401
import sympy  # noqa: F401

actual = {name: metadata.version(name) for name in direct}
if actual != expected:
    raise SystemExit(1)
PY
}

prepare_cache_root
if valid_cache; then
  printf '%s\n' "$CACHE"
  exit 0
fi

exec 9>"$LOCK_FILE"
flock 9
if valid_cache; then
  printf '%s\n' "$CACHE"
  exit 0
fi

"$ROOT/scripts/install-runtime.sh" >/dev/null
valid_cache || fail "runtime failed post-install validation"
printf '%s\n' "$CACHE"
