#!/usr/bin/env bash
set -euo pipefail
grep -q flock mcporter/scripts/ensure-runtime.sh
grep -q package-lock.json mcporter/scripts/install-runtime.sh
grep -q "ci --prefix" mcporter/scripts/install-runtime.sh
echo PASS
