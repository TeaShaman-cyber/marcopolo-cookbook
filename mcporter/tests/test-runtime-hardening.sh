#!/usr/bin/env bash
set -euo pipefail
grep -q flock mcporter/scripts/ensure-runtime.sh
grep -q package-lock.json mcporter/scripts/install-runtime.sh
grep -q "ci --prefix" mcporter/scripts/install-runtime.sh
grep -q "sha256sum -c -" marcopolo/README.md
grep -q "EXPECTED_SHA256" marcopolo/README.md
grep -q "flock" mcporter/scripts/install-runtime.sh
grep -q "ARCHIVE_TMP" mcporter/scripts/install-runtime.sh
grep -q "SHA_TMP" mcporter/scripts/install-runtime.sh
grep -q 'mv "$ARCHIVE_TMP" "$ARCHIVE"' mcporter/scripts/install-runtime.sh
grep -q 'mv "$SHA_TMP" "$SHA_FILE"' mcporter/scripts/install-runtime.sh
bash mcporter/tests/test_inventory_provenance.sh >/dev/null
echo PASS
