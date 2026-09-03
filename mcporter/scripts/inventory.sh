#!/usr/bin/env bash
set -euo pipefail
ROOT=/workspace/tools/mcporter
printf 'node='; node --version
printf 'npm='; npm --version
printf 'mcporter='; "$ROOT/bin/mcporter" --version
printf '%s\n' 'servers:'
"$ROOT/bin/mcporter" list --json
