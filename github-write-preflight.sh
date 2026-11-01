#!/bin/sh
set -eu

WRITE_CFG=${GH_WRITE_CONFIG:-/workspace/.config/gh-write}
AUTH_CHECK=${GITHUB_GIT_AUTH:-/workspace/marcopolo-cookbook/github-git-auth.sh}

blocked() {
	stage=$1 reason=$2
	printf 'GH_WRITE_PREFLIGHT BLOCKED stage=%s reason=%s\n' "$stage" "$reason" >&2
	exit 2
}

case ${1:-} in
--check)
	[ -r "$WRITE_CFG/hosts.yml" ] || blocked profile gh_write_profile_missing
	[ -x "$AUTH_CHECK" ] || blocked cookbook github_git_auth_missing
	"$AUTH_CHECK" --check >/dev/null 2>&1 || blocked helper github_git_auth_check_failed
	echo 'GH_WRITE_PREFLIGHT VERIFIED profile=gh-write helper=bound'
	;;
*)
	echo 'usage: github-write-preflight.sh --check' >&2
	exit 64
	;;
esac
