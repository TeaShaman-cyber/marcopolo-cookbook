#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$ROOT/runtime/versions.env"

PACKAGE="${AZURE_CLI_PACKAGE:-/workspace/tools/azure-cli/runtime/$PINNED_AZURE_CLI_PACKAGE}"
EXPECTED_SHA256="${AZURE_CLI_PACKAGE_SHA256:-$PINNED_AZURE_CLI_PACKAGE_SHA256}"
EXPECTED_VERSION="${AZURE_CLI_EXPECTED_VERSION:-$PINNED_AZURE_CLI_VERSION}"
RUNTIME_ID="${AZURE_CLI_RUNTIME_ID:-$PINNED_AZURE_CLI_RUNTIME_ID}"
TMP_BASE="${TMPDIR:-/tmp}"
UID_ACTUAL="$(id -u)"
CACHE_BASE="${AZURE_CLI_CACHE_BASE:-$TMP_BASE/marcopolo-azure-cli-$UID_ACTUAL}"

mkdir -p "$TMP_BASE"
if [[ -L "$CACHE_BASE" ]]; then
	echo "FAIL: cache root must not be a symlink: $CACHE_BASE" >&2
	exit 1
fi
if [[ ! -e "$CACHE_BASE" ]]; then
	mkdir -m 700 "$CACHE_BASE"
fi
[[ -d "$CACHE_BASE" ]] || {
	echo "FAIL: cache root is not a directory: $CACHE_BASE" >&2
	exit 1
}
CACHE_OWNER="$(stat -c '%u' "$CACHE_BASE")"
CACHE_MODE="$(stat -c '%a' "$CACHE_BASE")"
[[ "$CACHE_OWNER" == "$UID_ACTUAL" ]] || {
	echo "FAIL: cache root owner mismatch: $CACHE_BASE" >&2
	exit 1
}
[[ "$CACHE_MODE" == "700" ]] || {
	echo "FAIL: cache root mode must be 700: $CACHE_BASE" >&2
	exit 1
}

CACHE="$CACHE_BASE/$RUNTIME_ID"
AZ_ROOT="$CACHE/opt/az"
PY="$AZ_ROOT/bin/python3.14"
AZ="$AZ_ROOT/bin/az"
VALIDATION_CONFIG="$CACHE_BASE/.validation-config"

mkdir -p "$VALIDATION_CONFIG"
chmod 700 "$VALIDATION_CONFIG"

runtime_version() {
	AZURE_CONFIG_DIR="$VALIDATION_CONFIG" "$PY" "$AZ" version --output json 2>/dev/null |
		python3 -c 'import json,sys; print(json.load(sys.stdin).get("azure-cli",""))'
}

valid_cache() {
	[[ -d "$CACHE" && ! -L "$CACHE" && -x "$PY" && -f "$AZ" ]] || return 1
	[[ "$(runtime_version)" == "$EXPECTED_VERSION" ]] || return 1
}

if valid_cache; then
	exec "$PY" "$AZ" "$@"
fi

LOCK_FILE="$CACHE_BASE/.$RUNTIME_ID.lock"
exec 9>"$LOCK_FILE"
flock 9

if valid_cache; then
	exec "$PY" "$AZ" "$@"
fi

[[ -f "$PACKAGE" && ! -L "$PACKAGE" ]] || {
	echo "FAIL: Azure CLI package missing: $PACKAGE" >&2
	exit 2
}

if ! printf '%s  %s\n' "$EXPECTED_SHA256" "$PACKAGE" | sha256sum -c - >/dev/null 2>&1; then
	echo "FAIL: Azure CLI package checksum mismatch: $PACKAGE" >&2
	exit 1
fi

rm -rf "$CACHE"
STAGE="$(mktemp -d "$CACHE_BASE/.extract-XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT

dpkg-deb -x "$PACKAGE" "$STAGE"

PY_STAGE="$STAGE/opt/az/bin/python3.14"
AZ_STAGE="$STAGE/opt/az/bin/az"
[[ -x "$PY_STAGE" && -f "$AZ_STAGE" ]] || {
	echo "FAIL: incomplete Azure CLI package extraction" >&2
	exit 1
}

STAGE_VERSION="$(
	AZURE_CONFIG_DIR="$VALIDATION_CONFIG" "$PY_STAGE" "$AZ_STAGE" version --output json 2>/dev/null |
		python3 -c 'import json,sys; print(json.load(sys.stdin).get("azure-cli",""))'
)"
[[ "$STAGE_VERSION" == "$EXPECTED_VERSION" ]] || {
	echo "FAIL: Azure CLI version mismatch: expected $EXPECTED_VERSION got $STAGE_VERSION" >&2
	exit 1
}

mv "$STAGE" "$CACHE"
trap - EXIT

PY="$CACHE/opt/az/bin/python3.14"
AZ="$CACHE/opt/az/bin/az"
exec "$PY" "$AZ" "$@"
