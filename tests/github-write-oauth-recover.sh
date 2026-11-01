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
if [ "${1:-} ${2:-} ${3:-}" = "api -i user" ]; then
  printf '%s\n' "X-OAuth-Scopes: ${FAKE_GH_SCOPES:-repo, read:org, gist}"
  exit 0
fi
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

# an existing generic-ready profile missing canonical scopes must schedule recovery
MISSING_STATE="$TMP/missing-state"
MISSING_WRITE_CFG="$TMP/missing-gh-write"
MISSING_CRONTAB_FILE="$TMP/missing-crontab"
mkdir -p "$MISSING_WRITE_CFG"
printf '%s\n' synthetic >"$MISSING_WRITE_CFG/hosts.yml"
: >"$MISSING_CRONTAB_FILE"
missing_env="FAKE_CRONTAB_FILE=$MISSING_CRONTAB_FILE FAKE_GH_LOG=$GH_LOG FAKE_GH_SCOPES=repo,read:org,gist EXPECTED_WRITE_CFG=$MISSING_WRITE_CFG GH_WRITE_OAUTH_STATE_DIR=$MISSING_STATE GH_WRITE_CONFIG=$MISSING_WRITE_CFG GH_BIN=$BIN/gh CRONTAB_BIN=$BIN/crontab GITHUB_GIT_AUTH=$BIN/auth-check GITHUB_WRITE_PREFLIGHT=$BIN/preflight"
# shellcheck disable=SC2086
env $missing_env "$SCRIPT" --schedule-login >"$TMP/missing-schedule.out"
grep -F 'GH_WRITE_OAUTH SCHEDULED' "$TMP/missing-schedule.out" >/dev/null

# a profile already covering the canonical set may still short-circuit
READY_STATE="$TMP/ready-state"
READY_WRITE_CFG="$TMP/ready-gh-write"
READY_CRONTAB_FILE="$TMP/ready-crontab"
mkdir -p "$READY_WRITE_CFG"
printf '%s\n' synthetic >"$READY_WRITE_CFG/hosts.yml"
: >"$READY_CRONTAB_FILE"
ready_env="FAKE_CRONTAB_FILE=$READY_CRONTAB_FILE FAKE_GH_LOG=$GH_LOG FAKE_GH_SCOPES=repo,read:org,gist,project,codespace EXPECTED_WRITE_CFG=$READY_WRITE_CFG GH_WRITE_OAUTH_STATE_DIR=$READY_STATE GH_WRITE_CONFIG=$READY_WRITE_CFG GH_BIN=$BIN/gh CRONTAB_BIN=$BIN/crontab GITHUB_GIT_AUTH=$BIN/auth-check GITHUB_WRITE_PREFLIGHT=$BIN/preflight"
# shellcheck disable=SC2086
env $ready_env "$SCRIPT" --schedule-login >"$TMP/ready-schedule.out"
grep -F 'reason=already_ready' "$TMP/ready-schedule.out" >/dev/null

# requesting additional scopes must not short-circuit on generic repo-write readiness
SCOPED_STATE="$TMP/scoped-state"
SCOPED_WRITE_CFG="$TMP/scoped-gh-write"
SCOPED_CRONTAB_FILE="$TMP/scoped-crontab"
mkdir -p "$SCOPED_WRITE_CFG"
printf '%s\n' synthetic >"$SCOPED_WRITE_CFG/hosts.yml"
: >"$SCOPED_CRONTAB_FILE"
scoped_env="FAKE_CRONTAB_FILE=$SCOPED_CRONTAB_FILE FAKE_GH_LOG=$GH_LOG EXPECTED_WRITE_CFG=$SCOPED_WRITE_CFG GH_WRITE_OAUTH_STATE_DIR=$SCOPED_STATE GH_WRITE_CONFIG=$SCOPED_WRITE_CFG GH_BIN=$BIN/gh CRONTAB_BIN=$BIN/crontab GITHUB_GIT_AUTH=$BIN/auth-check GITHUB_WRITE_PREFLIGHT=$BIN/preflight GH_WRITE_OAUTH_SCOPES=project,read:project"
# shellcheck disable=SC2086
env $scoped_env "$SCRIPT" --schedule-login >"$TMP/scoped-schedule.out"
grep -F 'GH_WRITE_OAUTH SCHEDULED' "$TMP/scoped-schedule.out" >/dev/null
[ "$(grep -c 'GH_WRITE_OAUTH_RECOVERY' "$SCOPED_CRONTAB_FILE")" = 1 ]

# requesting one project-required capability must converge on the full canonical scope set
UNION_STATE="$TMP/union-state"
UNION_WRITE_CFG="$TMP/union-gh-write"
UNION_CRONTAB_FILE="$TMP/union-crontab"
UNION_GH_LOG="$TMP/union-gh-args.log"
: >"$UNION_CRONTAB_FILE"
: >"$UNION_GH_LOG"
union_env="FAKE_CRONTAB_FILE=$UNION_CRONTAB_FILE FAKE_GH_LOG=$UNION_GH_LOG EXPECTED_WRITE_CFG=$UNION_WRITE_CFG GH_WRITE_OAUTH_STATE_DIR=$UNION_STATE GH_WRITE_CONFIG=$UNION_WRITE_CFG GH_BIN=$BIN/gh CRONTAB_BIN=$BIN/crontab GITHUB_GIT_AUTH=$BIN/auth-check GITHUB_WRITE_PREFLIGHT=$BIN/preflight GH_WRITE_OAUTH_SCOPES=codespace"
# shellcheck disable=SC2086
env $union_env "$SCRIPT" --run-login
grep -F 'auth login -h github.com -p https -w --insecure-storage -s repo,read:org,gist,project,codespace' "$UNION_GH_LOG" >/dev/null

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
