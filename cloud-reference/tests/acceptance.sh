#!/bin/sh
set -eu

python3 -m unittest discover -s cloud-reference/tests -p 'test_*.py' -v
python3 -m json.tool cloud-reference/schemas/evidence-receipt.schema.json >/dev/null
python3 -m json.tool cloud-reference/queries/reviewed-sources.json >/dev/null
python3 -m json.tool cloud-reference/receipts/2026-09-03-mcp-marcopolo-dev.json >/dev/null
find cloud-reference -type d -name __pycache__ -prune -exec rm -rf {} +
python3 -m py_compile cloud-reference/lib/evidence.py cloud-reference/lib/hosting.py cloud-reference/lib/sources.py cloud-reference/lib/mcp.py cloud-reference/bin/hosting-identify cloud-reference/bin/mcp-registry-check cloud-reference/bin/cloud-docs cloud-reference/bin/waf-reference cloud-reference/bin/payload-shape-canary

for exe in hosting-identify mcp-registry-check cloud-docs waf-reference; do
  cloud-reference/bin/$exe --help >/dev/null
done
cloud-reference/bin/payload-shape-canary | python3 -m json.tool >/dev/null

TMP=${TMPDIR:-/tmp}/cloud-reference-acceptance.$$.json
trap 'rm -f "$TMP"' EXIT HUP INT TERM
cloud-reference/bin/hosting-identify mcp.marcopolo.dev --timeout 8 > "$TMP"
python3 -m json.tool "$TMP" >/dev/null
python3 - "$TMP" <<'PY'
import json, sys
r=json.load(open(sys.argv[1]))
assert r.get('target') == 'mcp.marcopolo.dev'
assert r.get('probe_kind') == 'hosting-identify'
PY

if git ls-files | grep -E '(^|/)(\.env($|\.)|\.vercel/|node_modules/|__pycache__/)|\.pyc$|\.log$|(^|/)traces?/' >/dev/null; then
  echo 'forbidden tracked runtime path' >&2
  exit 2
fi

if rg -I -n 'BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY|api[_-]?key[[:space:]]*[:=][[:space:]]*[^[:space:]]|authorization[[:space:]]*:[[:space:]]*bearer[[:space:]]+' cloud-reference docs/research/hosting-evidence 2>/dev/null; then
  echo 'secret marker found' >&2
  exit 3
fi

git diff --check
printf '%s\n' 'PASS cloud-reference acceptance'
