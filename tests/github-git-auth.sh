#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SCRIPT="$ROOT/github-git-auth.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
CONFIG="$TMP/gitconfig"
BIN="$TMP/bin"
mkdir -p "$BIN" "$TMP/gh-write"

cat > "$BIN/gh" <<'GH'
#!/bin/sh
set -eu
[ "${GH_CONFIG_DIR:-}" = "${EXPECTED_WRITE_CFG:-}" ] || exit 91
if [ "${1:-} ${2:-}" = "auth status" ]; then exit 0; fi
exit 0
GH
chmod +x "$BIN/gh"

# Seed the exact failure shape seen in the workspace: GitHub delegates to gh
# without binding the write profile.
git config --file "$CONFIG" --add credential.https://github.com.helper ''
git config --file "$CONFIG" --add credential.https://github.com.helper '!gh auth git-credential'

set +e
GIT_CONFIG_GLOBAL="$CONFIG" GH_BIN="$BIN/gh" GH_WRITE_CONFIG="$TMP/gh-write" \
  "$SCRIPT" --check >/dev/null 2>&1
before_rc=$?
set -e
[ "$before_rc" -ne 0 ] || { echo 'FAIL: unbound helper unexpectedly passed check' >&2; exit 1; }

EXPECTED_WRITE_CFG="$TMP/gh-write" GIT_CONFIG_GLOBAL="$CONFIG" GH_BIN="$BIN/gh" GH_WRITE_CONFIG="$TMP/gh-write" \
  "$SCRIPT" --install >/dev/null

expected="!GH_CONFIG_DIR=$TMP/gh-write $BIN/gh auth git-credential"
helpers=$(git config --file "$CONFIG" --get-all credential.https://github.com.helper)
expected_helpers=$(printf '\n%s' "$expected")
[ "$helpers" = "$expected_helpers" ] || {
  echo 'FAIL: helper chain was not reset and rebound to the write profile' >&2
  printf 'actual=%s\nexpected=%s\n' "$helpers" "$expected_helpers" >&2
  exit 1
}

EXPECTED_WRITE_CFG="$TMP/gh-write" GIT_CONFIG_GLOBAL="$CONFIG" GH_BIN="$BIN/gh" GH_WRITE_CONFIG="$TMP/gh-write" \
  "$SCRIPT" --check >/dev/null

# Idempotency: a second install must not duplicate helper entries.
EXPECTED_WRITE_CFG="$TMP/gh-write" GIT_CONFIG_GLOBAL="$CONFIG" GH_BIN="$BIN/gh" GH_WRITE_CONFIG="$TMP/gh-write" \
  "$SCRIPT" --install >/dev/null
count=$(git config --file "$CONFIG" --get-all credential.https://github.com.helper | wc -l | tr -d ' ')
[ "$count" = 2 ] || { echo "FAIL: expected reset plus one helper, got $count" >&2; exit 1; }

echo 'github-git-auth acceptance: PASS'
