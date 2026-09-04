#!/usr/bin/env bash
set -euo pipefail

ROOT="${MCPORTER_ROOT:-/workspace/tools/mcporter}"
. "$ROOT/runtime/versions.env"
BUNDLES="$ROOT/runtime/bundles"
ARCHIVE="$BUNDLES/$RUNTIME_BUNDLE.tar.gz"
SHA_FILE="$ARCHIVE.sha256"
CACHE_ROOT="${TMPDIR:-/tmp}/marcopolo-mcporter"
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

[[ -f "$ARCHIVE" && -f "$SHA_FILE" ]] || {
  echo "runtime archive missing; run $ROOT/scripts/install-runtime.sh" >&2
  exit 2
}
(cd "$BUNDLES" && sha256sum -c "$(basename "$SHA_FILE")" >/dev/null)

mkdir -p "$CACHE_ROOT"
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
