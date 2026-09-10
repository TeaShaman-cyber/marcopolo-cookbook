#!/bin/sh
set -eu

HOST=github.com
WRITE_CFG=${GH_WRITE_CONFIG:-/workspace/.config/gh-write}
GH_BIN=${GH_BIN:-/usr/local/bin/gh}
KEY=credential.https://github.com.helper

shell_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\"'\"'/g")"
}

HELPER="!GH_CONFIG_DIR=$(shell_quote "$WRITE_CFG") $(shell_quote "$GH_BIN") auth git-credential"

usage() {
  echo 'usage: github-git-auth.sh --install|--check' >&2
  exit 64
}

check_auth() {
  [ -x "$GH_BIN" ] || {
    echo "GITHUB_GIT_AUTH BLOCKED stage=auth reason=gh_missing" >&2
    exit 2
  }
  GH_CONFIG_DIR="$WRITE_CFG" "$GH_BIN" auth status --active -h "$HOST" >/dev/null 2>&1 || {
    echo "GITHUB_GIT_AUTH BLOCKED stage=auth reason=gh_write_profile_unavailable" >&2
    exit 2
  }
}

check_config() {
  helpers=$(git config --global --get-all "$KEY" 2>/dev/null || true)
  expected=$(printf '\n%s' "$HELPER")
  [ "$helpers" = "$expected" ] || {
    echo "GITHUB_GIT_AUTH BLOCKED stage=config reason=helper_mismatch" >&2
    exit 3
  }
}

case ${1:-} in
  --check)
    check_auth
    check_config
    echo 'GITHUB_GIT_AUTH VERIFIED host=github.com profile=gh-write'
    ;;
  --install)
    check_auth
    git config --global --unset-all "$KEY" 2>/dev/null || true
    git config --global --add "$KEY" ''
    git config --global --add "$KEY" "$HELPER"
    check_config
    echo 'GITHUB_GIT_AUTH INSTALLED host=github.com profile=gh-write'
    ;;
  *) usage ;;
esac
