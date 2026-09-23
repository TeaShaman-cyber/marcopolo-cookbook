#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$ROOT/session-search"
TARGET="${1:-/workspace/tools/session-search}"
FILES=(README.md search.sh acceptance.sh status.sh status.py runtime-bindings.sh)

mkdir -p "$TARGET"
STAGE=$(mktemp -d "$TARGET/.materialize.XXXXXX")
trap 'rm -rf "$STAGE"' EXIT

for name in "${FILES[@]}"; do
	cp "$SOURCE/$name" "$STAGE/$name"
done
chmod 0755 "$STAGE/search.sh" "$STAGE/acceptance.sh" "$STAGE/status.sh"
chmod 0644 "$STAGE/README.md" "$STAGE/status.py" "$STAGE/runtime-bindings.sh"

for name in "${FILES[@]}"; do
	mv -f "$STAGE/$name" "$TARGET/$name"
done

for name in "${FILES[@]}"; do
	cmp -s "$SOURCE/$name" "$TARGET/$name"
done

sha256sum "${FILES[@]/#/$TARGET/}"
