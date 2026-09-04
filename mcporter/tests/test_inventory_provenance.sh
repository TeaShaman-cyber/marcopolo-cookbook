#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ROOT="$TMP/mcporter"
CACHE="$TMP/cache"
FAKEBIN="$TMP/fakebin"
mkdir -p "$ROOT/scripts" "$ROOT/bin" "$CACHE/node/bin" "$CACHE/node/lib/node_modules/npm/bin" "$FAKEBIN"

cat > "$ROOT/scripts/ensure-runtime.sh" <<EOF
#!/usr/bin/env bash
printf '%s\\n' '$CACHE'
EOF
cat > "$CACHE/node/bin/node" <<'EOF'
#!/usr/bin/env bash
case "${1:-}" in
  --version) printf '%s\n' 'v24.20.0' ;;
  */npm-cli.js) printf '%s\n' '11.19.0' ;;
  *) exit 2 ;;
esac
EOF
cat > "$CACHE/node/lib/node_modules/npm/bin/npm-cli.js" <<'EOF'
#!/usr/bin/env node
EOF
ln -s ../lib/node_modules/npm/bin/npm-cli.js "$CACHE/node/bin/npm"
cat > "$ROOT/bin/mcporter" <<'EOF'
#!/usr/bin/env bash
case "${1:-}" in
  --version) printf '%s\n' '0.13.8' ;;
  list) printf '%s\n' '{"servers":[]}' ;;
  *) exit 2 ;;
esac
EOF
cat > "$FAKEBIN/node" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' 'v22.23.2'
EOF
cat > "$FAKEBIN/npm" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' '12.0.2'
EOF
chmod +x "$ROOT/scripts/ensure-runtime.sh" "$ROOT/bin/mcporter" \
  "$CACHE/node/bin/node" "$CACHE/node/lib/node_modules/npm/bin/npm-cli.js" \
  "$FAKEBIN/node" "$FAKEBIN/npm"

OUTPUT="$(MCPORTER_ROOT="$ROOT" PATH="$FAKEBIN:$PATH" "$REPO_ROOT/mcporter/scripts/inventory.sh")"
printf '%s\n' "$OUTPUT"
grep -Fxq 'node=v24.20.0' <<<"$OUTPUT"
grep -Fxq 'npm=11.19.0' <<<"$OUTPUT"
grep -Fxq 'mcporter=0.13.8' <<<"$OUTPUT"
! grep -Fq 'node=v22.23.2' <<<"$OUTPUT"
! grep -Fq 'npm=12.0.2' <<<"$OUTPUT"
printf '%s\n' PASS
