#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SCRIPT="$ROOT/github-git-auth.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
CONFIG="$TMP/gitconfig"
BIN="$TMP/bin dir's"
WRITE_CFG="$TMP/gh write;profile"
LOG="$TMP/gh.log"
mkdir -p "$BIN" "$WRITE_CFG"
: > "$LOG"

cat > "$BIN/gh" <<'GH'
#!/bin/sh
set -eu
printf '%s\n' "$*" >> "$GH_ARGS_LOG"
[ "${GH_CONFIG_DIR:-}" = "${EXPECTED_WRITE_CFG:-}" ] || exit 91
case "${1:-} ${2:-}" in
  "auth status")
    exit 0
    ;;
  "auth git-credential")
    if [ "${3:-}" = get ]; then
      printf '%s\n' 'username=synthetic-user' 'password=synthetic-password'
    fi
    exit 0
    ;;
esac
exit 0
GH
chmod +x "$BIN/gh"

git config --file "$CONFIG" --add credential.https://github.com.helper ''
git config --file "$CONFIG" --add credential.https://github.com.helper '!gh auth git-credential'

set +e
GH_ARGS_LOG="$LOG" EXPECTED_WRITE_CFG="$WRITE_CFG" GIT_CONFIG_GLOBAL="$CONFIG" \
  GH_BIN="$BIN/gh" GH_WRITE_CONFIG="$WRITE_CFG" "$SCRIPT" --check >/dev/null 2>&1
before_rc=$?
set -e
[ "$before_rc" -ne 0 ] || { echo 'FAIL: unbound helper unexpectedly passed check' >&2; exit 1; }

GH_ARGS_LOG="$LOG" EXPECTED_WRITE_CFG="$WRITE_CFG" GIT_CONFIG_GLOBAL="$CONFIG" \
  GH_BIN="$BIN/gh" GH_WRITE_CONFIG="$WRITE_CFG" "$SCRIPT" --install >/dev/null

helpers=$(git config --file "$CONFIG" --get-all credential.https://github.com.helper)
count=$(printf '%s\n' "$helpers" | wc -l | tr -d ' ')
[ "$count" = 2 ] || { echo "FAIL: expected reset plus one helper, got $count" >&2; exit 1; }

set +e
credential_out=$(
  printf '%s\n' 'protocol=https' 'host=github.com' '' |
    GH_ARGS_LOG="$LOG" EXPECTED_WRITE_CFG="$WRITE_CFG" \
    GIT_CONFIG_GLOBAL="$CONFIG" git credential fill 2>/dev/null
)
credential_rc=$?
set -e

fail=0
if [ "$credential_rc" -ne 0 ]; then
  echo 'FAIL: installed helper could not be invoked by git' >&2
  fail=1
fi
printf '%s\n' "$credential_out" | grep -Fx 'username=synthetic-user' >/dev/null 2>&1 || {
  echo 'FAIL: git credential helper did not return synthetic username' >&2
  fail=1
}
grep -Fx 'auth status --active -h github.com' "$LOG" >/dev/null 2>&1 || {
  echo 'FAIL: auth probe did not target only the active account' >&2
  fail=1
}
grep -Fx 'auth git-credential get' "$LOG" >/dev/null 2>&1 || {
  echo 'FAIL: git did not execute the configured gh credential helper' >&2
  fail=1
}
[ "$fail" -eq 0 ] || exit 1

GH_ARGS_LOG="$LOG" EXPECTED_WRITE_CFG="$WRITE_CFG" GIT_CONFIG_GLOBAL="$CONFIG" \
  GH_BIN="$BIN/gh" GH_WRITE_CONFIG="$WRITE_CFG" "$SCRIPT" --check >/dev/null

GH_ARGS_LOG="$LOG" EXPECTED_WRITE_CFG="$WRITE_CFG" GIT_CONFIG_GLOBAL="$CONFIG" \
  GH_BIN="$BIN/gh" GH_WRITE_CONFIG="$WRITE_CFG" "$SCRIPT" --install >/dev/null
count=$(git config --file "$CONFIG" --get-all credential.https://github.com.helper | wc -l | tr -d ' ')
[ "$count" = 2 ] || { echo "FAIL: expected reset plus one helper, got $count" >&2; exit 1; }

echo 'github-git-auth acceptance: PASS'
