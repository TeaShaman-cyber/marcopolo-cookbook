#!/usr/bin/env bash
set -euo pipefail

ROOT=/workspace/tools/mcporter
. "$ROOT/runtime/versions.env"
ARCHIVE="$ROOT/runtime/bundles/$RUNTIME_BUNDLE.tar.gz"
SHA_FILE="$ARCHIVE.sha256"

[[ -x "$ROOT/bin/mcporter" ]] || { echo "FAIL: wrapper missing"; exit 1; }
[[ -x "$ROOT/scripts/install-runtime.sh" ]] || { echo "FAIL: installer missing"; exit 1; }
[[ -x "$ROOT/scripts/ensure-runtime.sh" ]] || { echo "FAIL: cache loader missing"; exit 1; }
[[ -f "$ARCHIVE" && -f "$SHA_FILE" ]] || { echo "FAIL: runtime archive missing"; exit 1; }
(cd "$(dirname "$ARCHIVE")" && sha256sum -c "$(basename "$SHA_FILE")" >/dev/null)

CACHE="$("$ROOT/scripts/ensure-runtime.sh")"
NODE_ACTUAL="$("$CACHE/node/bin/node" --version)"
MCPORTER_ACTUAL="$("$ROOT/bin/mcporter" --version)"
[[ "$NODE_ACTUAL" == "$NODE_VERSION" ]] || { echo "FAIL: expected $NODE_VERSION got $NODE_ACTUAL"; exit 1; }
[[ "$MCPORTER_ACTUAL" == "$MCPORTER_VERSION" ]] || { echo "FAIL: expected $MCPORTER_VERSION got $MCPORTER_ACTUAL"; exit 1; }

printf 'PASS runtime=%s mcporter=%s cache=%s\n' "$NODE_ACTUAL" "$MCPORTER_ACTUAL" "$CACHE"
