#!/usr/bin/env bash
set -euo pipefail
ROOT=/workspace/tools/mcporter
[[ -x "$ROOT/bin/mcporter" ]] || { echo 'FAIL: wrapper missing'; exit 1; }
[[ -f "$ROOT/README.md" ]] || { echo 'FAIL: README missing'; exit 1; }
[[ -f "$ROOT/package-lock.json" ]] || { echo 'FAIL: lockfile missing'; exit 1; }
VERSION="$($ROOT/bin/mcporter --version)"
[[ -n "$VERSION" ]] || { echo 'FAIL: version empty'; exit 1; }
printf 'PASS version=%s\n' "$VERSION"
