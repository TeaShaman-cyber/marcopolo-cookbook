#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
TARGET="$TMP/RULES.md"
FAKE_BIN="$TMP/bin"
MARKER="$TMP/install-started"
mkdir -p "$FAKE_BIN"

cat > "$FAKE_BIN/install" <<'FAKE'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-m" ]]; then
  shift 2
fi
SOURCE="$1"
TARGET="$2"
: > "$TARGET"
: > "$FAKE_INSTALL_MARKER"
sleep 1
cat "$SOURCE" > "$TARGET"
chmod 0644 "$TARGET"
FAKE
chmod +x "$FAKE_BIN/install"

printf 'old projection\n' > "$TARGET"
OLD_INODE="$(stat -c %i "$TARGET")"

FAKE_INSTALL_MARKER="$MARKER" PATH="$FAKE_BIN:$PATH" \
  "$ROOT/rules/materialize-workspace-rules.sh" "$TARGET" &
PID=$!

for _ in $(seq 1 100); do
  if [[ -e "$MARKER" ]]; then
    if [[ "$(cat "$TARGET")" != "old projection" ]]; then
      kill "$PID" 2>/dev/null || true
      wait "$PID" 2>/dev/null || true
      printf 'FAIL existing projection changed before atomic publish\n' >&2
      exit 1
    fi
    break
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    break
  fi
  sleep 0.01
done

wait "$PID"
cmp -s "$ROOT/rules/workspace.RULES.md" "$TARGET"
NEW_INODE="$(stat -c %i "$TARGET")"
MODE="$(stat -c %a "$TARGET")"

if [[ "$OLD_INODE" == "$NEW_INODE" ]]; then
  printf 'FAIL target inode was not replaced\n' >&2
  exit 1
fi

if [[ "$MODE" != "644" ]]; then
  printf 'FAIL target mode=%s expected=644\n' "$MODE" >&2
  exit 1
fi

printf 'PASS materialize-workspace-rules\n'
