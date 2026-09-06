#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
TARGET="$TMP/RULES.md"
"$ROOT/rules/materialize-workspace-rules.sh" "$TARGET"
cmp -s "$ROOT/rules/workspace.RULES.md" "$TARGET"
printf 'PASS materialize-workspace-rules\n'
