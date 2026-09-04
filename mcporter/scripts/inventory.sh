#!/usr/bin/env bash
set -euo pipefail
ROOT="${MCPORTER_ROOT:-/workspace/tools/mcporter}"
CACHE="$("$ROOT/scripts/ensure-runtime.sh")"
printf 'node='; "$CACHE/node/bin/node" --version
printf 'npm='; "$CACHE/node/bin/node" "$CACHE/node/lib/node_modules/npm/bin/npm-cli.js" --version
printf 'mcporter='; "$ROOT/bin/mcporter" --version
printf '%s\n' 'servers:'
"$ROOT/bin/mcporter" list --json
