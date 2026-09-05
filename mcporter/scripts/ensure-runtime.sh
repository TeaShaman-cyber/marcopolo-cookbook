#!/usr/bin/env bash
set -euo pipefail

ROOT="${MCPORTER_ROOT:-/workspace/tools/mcporter}"
. "$ROOT/runtime/versions.env"
BUNDLES="$ROOT/runtime/bundles"
ARCHIVE="$BUNDLES/$RUNTIME_BUNDLE.tar.gz"
SHA_FILE="$ARCHIVE.sha256"
TMP_BASE="${TMPDIR:-/tmp}"
UID_ACTUAL="$(id -u)"
CACHE_ROOT="$TMP_BASE/marcopolo-mcporter-$UID_ACTUAL"

mkdir -p "$TMP_BASE"
if [[ -L "$CACHE_ROOT" ]]; then
  echo "FAIL: cache root must not be a symlink: $CACHE_ROOT" >&2
  exit 1
fi
if [[ ! -e "$CACHE_ROOT" ]]; then
  if ! mkdir -m 700 "$CACHE_ROOT" 2>/dev/null; then
    [[ -d "$CACHE_ROOT" ]] || { echo "FAIL: cannot create cache root: $CACHE_ROOT" >&2; exit 1; }
  fi
fi
[[ -d "$CACHE_ROOT" ]] || { echo "FAIL: cache root is not a directory: $CACHE_ROOT" >&2; exit 1; }
CACHE_OWNER="$(stat -c '%u' "$CACHE_ROOT")"
CACHE_MODE="$(stat -c '%a' "$CACHE_ROOT")"
[[ "$CACHE_OWNER" == "$UID_ACTUAL" ]] || { echo "FAIL: cache root owner mismatch: $CACHE_ROOT" >&2; exit 1; }
[[ "$CACHE_MODE" == "700" ]] || { echo "FAIL: cache root mode must be 700: $CACHE_ROOT" >&2; exit 1; }

CACHE="$CACHE_ROOT/$RUNTIME_BUNDLE"
NODE="$CACHE/node/bin/node"
CLI="$CACHE/workbench/node_modules/mcporter/dist/cli.js"

valid_cache() {
  [[ -x "$NODE" && -f "$CLI" ]] || return 1
  [[ "$("$NODE" --version)" == "$NODE_VERSION" ]] || return 1
  [[ "$("$NODE" "$CLI" --version)" == "$MCPORTER_VERSION" ]] || return 1
}

if valid_cache; then
  printf '%s\n' "$CACHE"
  exit 0
fi

# Coordinate archive/checksum readers with install-runtime.sh publication.
# The installer atomically renames each file while holding this lock; taking
# the same lock prevents a reader from observing a mixed archive/checksum pair.
mkdir -p "$BUNDLES"
PUBLISH_LOCK="$BUNDLES/.${RUNTIME_BUNDLE}.publish.lock"
exec 8>"$PUBLISH_LOCK"
flock 8

[[ -f "$ARCHIVE" && -f "$SHA_FILE" ]] || {
  echo "runtime archive missing; run $ROOT/scripts/install-runtime.sh" >&2
  exit 2
}
(cd "$BUNDLES" && sha256sum -c "$(basename "$SHA_FILE")" >/dev/null)

LOCK_FILE="$CACHE_ROOT/.${RUNTIME_BUNDLE}.lock"
exec 9>"$LOCK_FILE"
flock 9

# Another invocation may have published a valid cache while this process waited.
if valid_cache; then
  printf '%s\n' "$CACHE"
  exit 0
fi
rm -rf "$CACHE"
STAGE="$(mktemp -d "$CACHE_ROOT/.extract-XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
tar -xzf "$ARCHIVE" -C "$STAGE"

NODE_STAGE="$STAGE/node/bin/node"
CLI_STAGE="$STAGE/workbench/node_modules/mcporter/dist/cli.js"
[[ -x "$NODE_STAGE" && -f "$CLI_STAGE" ]] || { echo "FAIL: incomplete runtime archive" >&2; exit 1; }
[[ "$("$NODE_STAGE" --version)" == "$NODE_VERSION" ]] || { echo "FAIL: Node version mismatch" >&2; exit 1; }
[[ "$("$NODE_STAGE" "$CLI_STAGE" --version)" == "$MCPORTER_VERSION" ]] || { echo "FAIL: mcporter version mismatch" >&2; exit 1; }

mv "$STAGE" "$CACHE"
trap - EXIT
printf '%s\n' "$CACHE"
