#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$ROOT/rules/workspace.RULES.md"
TARGET="${1:-/workspace/RULES.md}"
TMP="${TARGET}.tmp.$$"
trap 'rm -f "$TMP"' EXIT
cp "$SOURCE" "$TMP"
install -m 0644 "$TMP" "$TARGET"
cmp -s "$SOURCE" "$TARGET"
sha256sum "$SOURCE" "$TARGET"
