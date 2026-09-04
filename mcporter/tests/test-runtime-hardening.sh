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
# Acceptance must not independently read the archive/checksum publication pair.
# ensure-runtime.sh is the coordinated reader and owns publication locking.
if grep -q 'sha256sum' mcporter/tests/acceptance.sh; then
  echo 'FAIL: acceptance bypasses coordinated archive reader' >&2
  exit 1
fi
grep -Fq 'CACHE="$("$ROOT/scripts/ensure-runtime.sh")"' mcporter/tests/acceptance.sh
