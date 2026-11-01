#!/bin/sh
set -eu
umask 077

D=${GCX_AUTH_DIR:-/workspace/.config/gcx-tealaphid71}
GCX=${GCX_BIN:-/workspace/tools/gcx/bin/gcx}
SELF=${GCX_HELPER_PATH:-/workspace/tools/gcx/gcx-oauth-relay.sh}
MARKER=GCX_OAUTH_RELAY_ONESHOT

fail() {
	echo "GCX_OAUTH BLOCKED: $1" >&2
	exit 2
}

cron_list() {
	crontab -l 2>/dev/null || true
}

cron_remove() {
	t=$(mktemp)
	cron_list | grep -v -F "$MARKER" >"$t" || true
	crontab "$t"
	rm -f "$t"
}

cron_pending() {
	cron_list | grep -F "$MARKER" >/dev/null
}

case "${1:---help}" in
--schedule)
	[ "${GCX_FILE_STORAGE_APPROVED:-}" = "1" ] || fail "file_storage_requires_explicit_approval"
	[ -x "$GCX" ] || fail "gcx_binary_missing"
	[ -x "$SELF" ] || fail "installed_helper_missing"
	[ ! -L "$D" ] || fail "profile_directory_symlink"
	mkdir -p "$D"
	chmod 700 "$D"
	[ ! -d "$D/started.lock" ] || fail "previous_run_requires_cleanup"
	if cron_pending; then
		echo "GCX_OAUTH SCHEDULED"
		exit 0
	fi
	rm -f "$D/login.log" "$D/tunnel-origin.txt" "$D/result"
	printf "approved\n" >"$D/approved.once"
	chmod 600 "$D/approved.once"
	t=$(mktemp)
	cron_list >"$t"
	printf '* * * * * %s --run # %s\n' "$SELF" "$MARKER" >>"$t"
	crontab "$t"
	rm -f "$t"
	echo "GCX_OAUTH SCHEDULED"
	;;
--run)
	[ -d "$D" ] || fail "profile_directory_missing"
	[ -f "$D/approved.once" ] || fail "approved_schedule_missing"
	rm -f "$D/approved.once"
	if ! mkdir "$D/started.lock" 2>/dev/null; then
		exit 0
	fi
	cron_remove
	: >"$D/login.log"
	chmod 600 "$D/login.log"
	# SSH output is filtered to a temporary public origin only.
	# Every callback path and query remains browser-to-CLI, never in these logs.
	setsid sh -c 'ssh -n -T -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 -o ServerAliveInterval=20 -o ExitOnForwardFailure=yes -R 80:127.0.0.1:20000 nokey@localhost.run 2>&1 | awk '\''/tunneled with tls termination/ {for(i=1;i<=NF;i++){gsub(/\r/,"",$i);if($i ~ /^https:\/\/[-a-zA-Z0-9.]+$/){print $i; fflush()}}}'\'' ' >"$D/tunnel-origin.txt" &
	tunnel_sid=$!
	cleanup() {
		/usr/bin/kill -TERM -- "-$tunnel_sid" 2>/dev/null || true
	}
	trap cleanup EXIT HUP INT TERM
	rc=0
	GCX_KEYCHAIN=off timeout 610 "$GCX" --agent login tealaphid71 \
		--server https://tealaphid71.grafana.net --oauth \
		--oauth-callback-port 20000 --yes \
		--config "$D/config.yaml" >"$D/login.log" 2>&1 || rc=$?
	printf '%s\n' "$rc" >"$D/result"
	;;
--status)
	if [ -f "$D/result" ]; then
		printf 'GCX_OAUTH FINISHED exit=%s\n' "$(cat "$D/result")"
	elif [ -d "$D/started.lock" ]; then
		echo "GCX_OAUTH RUNNING"
	elif cron_pending; then
		echo "GCX_OAUTH SCHEDULED"
	else
		echo "GCX_OAUTH IDLE"
	fi
	if [ -s "$D/tunnel-origin.txt" ]; then
		printf 'TUNNEL_ORIGIN='
		head -1 "$D/tunnel-origin.txt"
	fi
	if [ -f "$D/login.log" ]; then
		grep -E '^  https://tealaphid71\.grafana\.net/a/grafana-assistant-app/cli/auth\?|^Verification code:|^Waiting for authentication' "$D/login.log" | head -5 || true
	fi
	;;
--cancel)
	cron_remove
	[ -d "$D/started.lock" ] || rm -f "$D/approved.once"
	echo "GCX_OAUTH SCHEDULE_REMOVED"
	;;
--cleanup)
	[ ! -d "$D/started.lock" ] || [ -f "$D/result" ] || fail "active_or_unknown_run"
	cron_remove
	rm -f "$D/login.log" "$D/tunnel-origin.txt" "$D/result" "$D/approved.once"
	rmdir "$D/started.lock" 2>/dev/null || true
	echo "GCX_OAUTH TEMPORARY_ARTIFACTS_REMOVED"
	;;
--help)
	echo "usage: gcx-oauth-relay.sh --schedule|--status|--cancel|--cleanup"
	echo "set GCX_FILE_STORAGE_APPROVED=1 only after user approves unencrypted private-file storage"
	;;
*)
	fail "unknown_command"
	;;
esac
