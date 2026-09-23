#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$ROOT/session-search"
TARGET="${1:-/workspace/tools/session-search}"
FILES=(README.md search.sh acceptance.sh status.sh status.py runtime-bindings.sh local-projection.sh local_projection.py)

mkdir -p "$TARGET"
STAGE=$(mktemp -d "$TARGET/.materialize.XXXXXX")
trap 'rm -rf "$STAGE"' EXIT

for name in "${FILES[@]}"; do
	cp "$SOURCE/$name" "$STAGE/$name"
done
chmod 0755 "$STAGE/search.sh" "$STAGE/acceptance.sh" "$STAGE/status.sh" "$STAGE/local-projection.sh"
chmod 0644 "$STAGE/README.md" "$STAGE/status.py" "$STAGE/runtime-bindings.sh" "$STAGE/local_projection.py"

for name in "${FILES[@]}"; do
	mv -f "$STAGE/$name" "$TARGET/$name"
done

for name in "${FILES[@]}"; do
	cmp -s "$SOURCE/$name" "$TARGET/$name"
done

sha256sum "${FILES[@]/#/$TARGET/}"
