#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SCRIPT="$ROOT/github-write-oauth-recover.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
BIN="$TMP/bin"
STATE="$TMP/state"
WRITE_CFG="$TMP/gh-write"
CRONTAB_FILE="$TMP/crontab"
GH_LOG="$TMP/gh-args.log"
mkdir -p "$BIN"
: >"$CRONTAB_FILE"
: >"$GH_LOG"

cat >"$BIN/crontab" <<'CRON'
#!/bin/sh
set -eu
file=${FAKE_CRONTAB_FILE:?}
case ${1:-} in
-l)
  cat "$file"
  ;;
'')
  cat >"$file"
  ;;
*)
  echo "unexpected crontab args: $*" >&2
  exit 91
  ;;
esac
CRON
chmod +x "$BIN/crontab"

cat >"$BIN/gh" <<'GH'
#!/bin/sh
set -eu
printf '%s\n' "$*" >>"$FAKE_GH_LOG"
[ "${GH_CONFIG_DIR:-}" = "${EXPECTED_WRITE_CFG:?}" ] || exit 92
if [ "$1 $2" = "auth login" ]; then
  printf '%s\n' '! First copy your one-time code: TEST-CODE' \
    'Open this URL to continue in your web browser: https://github.com/login/device' \
    'token=SHOULD_NOT_SURFACE'
  mkdir -p "$GH_CONFIG_DIR"
  printf '%s\n' synthetic >"$GH_CONFIG_DIR/hosts.yml"
  exit 0
fi
exit 93
GH
chmod +x "$BIN/gh"

cat >"$BIN/auth-check" <<'AUTH'
#!/bin/sh
set -eu
[ "$1" = --install ] || exit 94
exit 0
AUTH
chmod +x "$BIN/auth-check"

cat >"$BIN/preflight" <<'PRE'
#!/bin/sh
set -eu
[ "$1" = --check ] || exit 95
[ -r "${EXPECTED_WRITE_CFG:?}/hosts.yml" ] || exit 96
exit 0
PRE
chmod +x "$BIN/preflight"

common_env="FAKE_CRONTAB_FILE=$CRONTAB_FILE FAKE_GH_LOG=$GH_LOG EXPECTED_WRITE_CFG=$WRITE_CFG GH_WRITE_OAUTH_STATE_DIR=$STATE GH_WRITE_CONFIG=$WRITE_CFG GH_BIN=$BIN/gh CRONTAB_BIN=$BIN/crontab GITHUB_GIT_AUTH=$BIN/auth-check GITHUB_WRITE_PREFLIGHT=$BIN/preflight"

# schedule is idempotent and creates exactly one tagged cron entry
# shellcheck disable=SC2086
env $common_env "$SCRIPT" --schedule-login >"$TMP/schedule1.out"
# shellcheck disable=SC2086
env $common_env "$SCRIPT" --schedule-login >"$TMP/schedule2.out"
grep -F 'GH_WRITE_OAUTH SCHEDULED' "$TMP/schedule1.out" >/dev/null
grep -F 'GH_WRITE_OAUTH SCHEDULED' "$TMP/schedule2.out" >/dev/null
[ "$(grep -c 'GH_WRITE_OAUTH_RECOVERY' "$CRONTAB_FILE")" = 1 ]

# run is one-shot, removes the cron entry, creates/validates gh-write, and records VERIFIED
# shellcheck disable=SC2086
env $common_env "$SCRIPT" --run-login
! grep -q 'GH_WRITE_OAUTH_RECOVERY' "$CRONTAB_FILE"
[ -r "$WRITE_CFG/hosts.yml" ]
grep -Fx 'GH_WRITE_OAUTH VERIFIED profile=gh-write helper=bound' "$STATE/result" >/dev/null
[ "$(grep -c '^auth login ' "$GH_LOG")" = 1 ]

# re-running cannot start another auth flow
# shellcheck disable=SC2086
env $common_env "$SCRIPT" --run-login
[ "$(grep -c '^auth login ' "$GH_LOG")" = 1 ]

# status exposes only the public device prompt plus state, never arbitrary raw login output
# shellcheck disable=SC2086
env $common_env "$SCRIPT" --status >"$TMP/status.out"
grep -F 'TEST-CODE' "$TMP/status.out" >/dev/null
grep -F 'https://github.com/login/device' "$TMP/status.out" >/dev/null
grep -F 'GH_WRITE_OAUTH VERIFIED profile=gh-write helper=bound' "$TMP/status.out" >/dev/null
! grep -F 'SHOULD_NOT_SURFACE' "$TMP/status.out" >/dev/null

# cleanup removes only recovery state/schedule, not the resulting write profile
# shellcheck disable=SC2086
env $common_env "$SCRIPT" --cleanup
test ! -e "$STATE"
test -r "$WRITE_CFG/hosts.yml"

echo 'github-write-oauth-recover acceptance: PASS'
