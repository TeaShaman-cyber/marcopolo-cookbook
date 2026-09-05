#!/usr/bin/env bash
set -euo pipefail

ROOT=/workspace/tools/mcporter
. "$ROOT/runtime/versions.env"
BUNDLES="$ROOT/runtime/bundles"
ARCHIVE="$BUNDLES/$RUNTIME_BUNDLE.tar.gz"
SHA_FILE="$ARCHIVE.sha256"

mkdir -p "$BUNDLES"
PUBLISH_LOCK="$BUNDLES/.${RUNTIME_BUNDLE}.publish.lock"
exec 8>"$PUBLISH_LOCK"
flock 8

if [[ -f "$ARCHIVE" && -f "$SHA_FILE" ]] && (cd "$BUNDLES" && sha256sum -c "$(basename "$SHA_FILE")" >/dev/null 2>&1); then
  printf 'already-built archive=%s\n' "$ARCHIVE"
  exit 0
fi

TMP="$(mktemp -d /tmp/mcporter-build-XXXXXX)"
ARCHIVE_TMP=""
SHA_TMP=""
cleanup() {
  rm -rf "$TMP"
  [[ -z "$ARCHIVE_TMP" ]] || rm -f "$ARCHIVE_TMP"
  [[ -z "$SHA_TMP" ]] || rm -f "$SHA_TMP"
}
trap cleanup EXIT
STAGE="$TMP/stage"
mkdir -p "$STAGE/node" "$STAGE/workbench"

TARBALL="node-$NODE_VERSION-linux-$NODE_ARCH.tar.gz"
URL="https://nodejs.org/dist/$NODE_VERSION/$TARBALL"
curl -fsSL "$URL" -o "$TMP/$TARBALL"
printf '%s  %s\n' "$NODE_SHA256" "$TMP/$TARBALL" | sha256sum -c -
tar -xzf "$TMP/$TARBALL" -C "$STAGE/node" --strip-components=1

cp "$ROOT/package.json" "$ROOT/package-lock.json" "$STAGE/workbench/"

"$STAGE/node/bin/node" "$STAGE/node/lib/node_modules/npm/bin/npm-cli.js" \
  ci --prefix "$STAGE/workbench" --ignore-scripts --no-audit --no-fund

NODE_ACTUAL="$("$STAGE/node/bin/node" --version)"
MCPORTER_ACTUAL="$("$STAGE/node/bin/node" "$STAGE/workbench/node_modules/mcporter/dist/cli.js" --version)"
[[ "$NODE_ACTUAL" == "$NODE_VERSION" ]] || { echo "FAIL: built Node $NODE_ACTUAL" >&2; exit 1; }
[[ "$MCPORTER_ACTUAL" == "$MCPORTER_VERSION" ]] || { echo "FAIL: built mcporter $MCPORTER_ACTUAL" >&2; exit 1; }

# Produce one persistent NFS artifact. Build off-path, stage complete files
# beside the destination, then atomically rename them while holding the
# publication lock so concurrent installers cannot interleave writes.
tar -C "$STAGE" -cf "$TMP/$RUNTIME_BUNDLE.tar" node workbench
gzip -n "$TMP/$RUNTIME_BUNDLE.tar"

PUBLISH_BASE="$(mktemp "$BUNDLES/.${RUNTIME_BUNDLE}.publish-XXXXXX")"
rm -f "$PUBLISH_BASE"
ARCHIVE_TMP="$PUBLISH_BASE.tar.gz"
SHA_TMP="$PUBLISH_BASE.sha256"
cp "$TMP/$RUNTIME_BUNDLE.tar.gz" "$ARCHIVE_TMP"
ARCHIVE_DIGEST="$(sha256sum "$ARCHIVE_TMP" | awk '{print $1}')"
printf '%s  %s\n' "$ARCHIVE_DIGEST" "$ARCHIVE_TMP" | sha256sum -c -
printf '%s  %s\n' "$ARCHIVE_DIGEST" "$(basename "$ARCHIVE")" > "$SHA_TMP"

mv "$ARCHIVE_TMP" "$ARCHIVE"
ARCHIVE_TMP=""
mv "$SHA_TMP" "$SHA_FILE"
SHA_TMP=""
(cd "$BUNDLES" && sha256sum -c "$(basename "$SHA_FILE")")

printf 'built archive=%s node=%s mcporter=%s\n' "$ARCHIVE" "$NODE_ACTUAL" "$MCPORTER_ACTUAL"
