#!/usr/bin/env bash
set -euo pipefail

ROOT=/workspace/tools/mcporter
. "$ROOT/runtime/versions.env"
BUNDLES="$ROOT/runtime/bundles"
ARCHIVE="$BUNDLES/$RUNTIME_BUNDLE.tar.gz"
SHA_FILE="$ARCHIVE.sha256"

if [[ -f "$ARCHIVE" && -f "$SHA_FILE" ]] && (cd "$BUNDLES" && sha256sum -c "$(basename "$SHA_FILE")" >/dev/null 2>&1); then
  printf 'already-built archive=%s\n' "$ARCHIVE"
  exit 0
fi

TMP="$(mktemp -d /tmp/mcporter-build-XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
STAGE="$TMP/stage"
mkdir -p "$STAGE/node" "$STAGE/workbench"

TARBALL="node-$NODE_VERSION-linux-$NODE_ARCH.tar.gz"
URL="https://nodejs.org/dist/$NODE_VERSION/$TARBALL"
curl -fsSL "$URL" -o "$TMP/$TARBALL"
printf '%s  %s\n' "$NODE_SHA256" "$TMP/$TARBALL" | sha256sum -c -
tar -xzf "$TMP/$TARBALL" -C "$STAGE/node" --strip-components=1

cat > "$STAGE/workbench/package.json" <<PKG
{
  "name": "marcopolo-mcporter-runtime",
  "private": true,
  "version": "0.1.0",
  "dependencies": {
    "mcporter": "$MCPORTER_VERSION"
  }
}
PKG

"$STAGE/node/bin/node" "$STAGE/node/lib/node_modules/npm/bin/npm-cli.js" \
  install --prefix "$STAGE/workbench" --ignore-scripts --no-audit --no-fund

NODE_ACTUAL="$("$STAGE/node/bin/node" --version)"
MCPORTER_ACTUAL="$("$STAGE/node/bin/node" "$STAGE/workbench/node_modules/mcporter/dist/cli.js" --version)"
[[ "$NODE_ACTUAL" == "$NODE_VERSION" ]] || { echo "FAIL: built Node $NODE_ACTUAL" >&2; exit 1; }
[[ "$MCPORTER_ACTUAL" == "$MCPORTER_VERSION" ]] || { echo "FAIL: built mcporter $MCPORTER_ACTUAL" >&2; exit 1; }

# Produce one persistent NFS artifact. Runtime trees stay on local temporary storage.
tar -C "$STAGE" -cf "$TMP/$RUNTIME_BUNDLE.tar" node workbench
gzip -n "$TMP/$RUNTIME_BUNDLE.tar"
mkdir -p "$BUNDLES"
cp "$TMP/$RUNTIME_BUNDLE.tar.gz" "$ARCHIVE"
(cd "$BUNDLES" && sha256sum "$(basename "$ARCHIVE")" > "$(basename "$SHA_FILE")")
(cd "$BUNDLES" && sha256sum -c "$(basename "$SHA_FILE")")

printf 'built archive=%s node=%s mcporter=%s\n' "$ARCHIVE" "$NODE_ACTUAL" "$MCPORTER_ACTUAL"
