#!/bin/sh
set -eu
umask 077

HOST=${GH_WRITE_OAUTH_HOST:-github.com}
WRITE_CFG=${GH_WRITE_CONFIG:-/workspace/.config/gh-write}
STATE_DIR=${GH_WRITE_OAUTH_STATE_DIR:-/tmp/gh-write-oauth-recover}
CRONTAB_BIN=${CRONTAB_BIN:-crontab}
AUTH_CHECK=${GITHUB_GIT_AUTH:-/workspace/marcopolo-cookbook/github-git-auth.sh}
PREFLIGHT=${GITHUB_WRITE_PREFLIGHT:-/workspace/marcopolo-cookbook/github-write-preflight.sh}
WORKSPACE_GH_BIN=${GH_WORKSPACE_BIN:-/workspace/.local/bin/gh}
SYSTEM_GH_BIN=${GH_SYSTEM_BIN:-/usr/local/bin/gh}
SCOPES=${GH_WRITE_OAUTH_SCOPES:-}
MARKER=GH_WRITE_OAUTH_RECOVERY
SELF=$(CDPATH= cd -- "$(dirname "$0")" && pwd)/$(basename "$0")

if [ -n "${GH_BIN:-}" ]; then
	:
elif [ -x "$WORKSPACE_GH_BIN" ]; then
	GH_BIN=$WORKSPACE_GH_BIN
else
	GH_BIN=$SYSTEM_GH_BIN
fi

blocked() {
	stage=$1 reason=$2
	printf 'GH_WRITE_OAUTH BLOCKED stage=%s reason=%s\n' "$stage" "$reason" >&2
	exit 2
}

failed() {
	stage=$1 reason=$2
	rc=${3:-3}
	mkdir -p "$STATE_DIR"
	printf 'GH_WRITE_OAUTH FAILED stage=%s reason=%s\n' "$stage" "$reason" >"$STATE_DIR/result"
	exit "$rc"
}

shell_quote() {
	printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\"'\"'/g")"
}

validate_state_dir() {
	case "$STATE_DIR" in
	"" | / | /tmp | /workspace)
		blocked config unsafe_state_dir
		;;
	esac
}

cron_list() {
	"$CRONTAB_BIN" -l 2>/dev/null || true
}

cron_has_entry() {
	cron_list | grep -F "$MARKER" >/dev/null 2>&1
}

remove_cron_entry() {
	tmp=$(mktemp)
	cron_list | grep -v -F "$MARKER" >"$tmp" || true
	"$CRONTAB_BIN" <"$tmp"
	rm -f "$tmp"
}

install_cron_entry() {
	tmp=$(mktemp)
	cron_list | grep -v -F "$MARKER" >"$tmp" || true
	line="* * * * * GH_WRITE_OAUTH_STATE_DIR=$(shell_quote "$STATE_DIR") GH_WRITE_CONFIG=$(shell_quote "$WRITE_CFG") GH_BIN=$(shell_quote "$GH_BIN") CRONTAB_BIN=$(shell_quote "$CRONTAB_BIN") GITHUB_GIT_AUTH=$(shell_quote "$AUTH_CHECK") GITHUB_WRITE_PREFLIGHT=$(shell_quote "$PREFLIGHT")"
	if [ -n "$SCOPES" ]; then
		line="$line GH_WRITE_OAUTH_SCOPES=$(shell_quote "$SCOPES")"
	fi
	line="$line $(shell_quote "$SELF") --run-login # $MARKER"
	printf '%s\n' "$line" >>"$tmp"
	"$CRONTAB_BIN" <"$tmp"
	rm -f "$tmp"
}

ensure_dependencies() {
	command -v "$CRONTAB_BIN" >/dev/null 2>&1 || blocked scheduler crontab_missing
	[ -x "$GH_BIN" ] || blocked auth gh_missing
	[ -x "$AUTH_CHECK" ] || blocked cookbook github_git_auth_missing
	[ -x "$PREFLIGHT" ] || blocked cookbook github_write_preflight_missing
}

profile_ready() {
	[ -r "$WRITE_CFG/hosts.yml" ] || return 1
	"$AUTH_CHECK" --install >/dev/null 2>&1 || return 1
	"$PREFLIGHT" --check >/dev/null 2>&1
}

case ${1:-} in
--schedule-login)
	validate_state_dir
	ensure_dependencies
	if [ -z "$SCOPES" ] && profile_ready; then
		echo 'GH_WRITE_OAUTH VERIFIED profile=gh-write helper=bound reason=already_ready'
		exit 0
	fi
	mkdir -p "$STATE_DIR"
	chmod 700 "$STATE_DIR"
	if cron_has_entry; then
		echo "GH_WRITE_OAUTH SCHEDULED state_dir=$STATE_DIR"
		exit 0
	fi
	[ ! -d "$STATE_DIR/started.lock" ] || blocked state existing_flow_requires_cleanup
	rm -f "$STATE_DIR/login.log" "$STATE_DIR/result" "$STATE_DIR/started"
	install_cron_entry
	echo "GH_WRITE_OAUTH SCHEDULED state_dir=$STATE_DIR"
	;;
--run-login)
	validate_state_dir
	ensure_dependencies
	mkdir -p "$STATE_DIR"
	chmod 700 "$STATE_DIR"
	if ! mkdir "$STATE_DIR/started.lock" 2>/dev/null; then
		exit 0
	fi
	remove_cron_entry
	date -u +%s >"$STATE_DIR/started"
	: >"$STATE_DIR/login.log"
	chmod 600 "$STATE_DIR/login.log"
	set +e
	if [ -n "$SCOPES" ]; then
		printf '\n' | GH_BROWSER=echo GH_CONFIG_DIR="$WRITE_CFG" "$GH_BIN" auth login -h "$HOST" -p https -w --insecure-storage -s "$SCOPES" >"$STATE_DIR/login.log" 2>&1
	else
		printf '\n' | GH_BROWSER=echo GH_CONFIG_DIR="$WRITE_CFG" "$GH_BIN" auth login -h "$HOST" -p https -w --insecure-storage >"$STATE_DIR/login.log" 2>&1
	fi
	login_rc=$?
	set -e
	[ "$login_rc" -eq 0 ] || failed login gh_auth_login_failed "$login_rc"
	[ -r "$WRITE_CFG/hosts.yml" ] || failed profile gh_write_profile_missing_after_login
	"$AUTH_CHECK" --install >/dev/null 2>&1 || failed helper github_git_auth_install_failed
	"$PREFLIGHT" --check >/dev/null 2>&1 || failed preflight github_write_preflight_failed
	printf '%s\n' 'GH_WRITE_OAUTH VERIFIED profile=gh-write helper=bound' >"$STATE_DIR/result"
	;;
--status)
	validate_state_dir
	if [ -r "$STATE_DIR/login.log" ]; then
		grep -E 'one-time code:|Open this URL to continue in your web browser: https://github\.com/login/device' "$STATE_DIR/login.log" | head -n 4 || true
	fi
	if [ -r "$STATE_DIR/result" ]; then
		cat "$STATE_DIR/result"
	elif [ -d "$STATE_DIR/started.lock" ]; then
		echo 'GH_WRITE_OAUTH RUNNING'
	elif cron_has_entry; then
		echo 'GH_WRITE_OAUTH SCHEDULED'
	else
		echo 'GH_WRITE_OAUTH IDLE'
	fi
	;;
--cleanup)
	validate_state_dir
	command -v "$CRONTAB_BIN" >/dev/null 2>&1 || blocked scheduler crontab_missing
	remove_cron_entry
	rm -rf "$STATE_DIR"
	echo 'GH_WRITE_OAUTH CLEAN'
	;;
*)
	echo 'usage: github-write-oauth-recover.sh --schedule-login|--status|--cleanup' >&2
	exit 64
	;;
esac
