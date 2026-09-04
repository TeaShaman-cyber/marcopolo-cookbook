#!/usr/bin/env bash
set -euo pipefail
grep -q flock mcporter/scripts/ensure-runtime.sh
grep -q package-lock.json mcporter/scripts/install-runtime.sh
grep -q "ci --prefix" mcporter/scripts/install-runtime.sh
bash mcporter/tests/test_inventory_provenance.sh >/dev/null
echo PASS
