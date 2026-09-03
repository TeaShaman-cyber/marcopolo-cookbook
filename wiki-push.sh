#!/bin/sh
set -eu

WRITE_CFG=/workspace/.config/gh-write
CHECKOUT=${1:-.}
export GH_CONFIG_DIR="$WRITE_CFG"

blocked() {
  stage=$1 reason=$2
  printf 'WIKI_PUSH BLOCKED stage=%s reason=%s\n' "$stage" "$reason"
  exit "${3:-2}"
}

failed() {
  stage=$1 reason=$2 code=$3
  printf 'WIKI_PUSH FAILED stage=%s reason=%s\n' "$stage" "$reason"
  exit "$code"
}

if ! git -C "$CHECKOUT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  blocked checkout not_git_worktree
fi

REMOTE=$(git -C "$CHECKOUT" remote get-url origin 2>/dev/null || true)
case "$REMOTE" in
  *.wiki.git|*.wiki.git/) ;;
  *) blocked remote not_wiki_remote ;;
esac

BRANCH=$(git -C "$CHECKOUT" symbolic-ref --quiet --short HEAD 2>/dev/null || true)
[ -n "$BRANCH" ] || blocked checkout detached_head

if ! gh auth status -h github.com >/dev/null 2>&1; then
  blocked auth gh_write_profile_unavailable
fi

if ! git -C "$CHECKOUT" push --dry-run origin "$BRANCH" >/dev/null 2>&1; then
  blocked preflight write_probe_failed 3
fi

if ! git -C "$CHECKOUT" push origin "$BRANCH"; then
  failed push git_push_failed 4
fi

LOCAL_SHA=$(git -C "$CHECKOUT" rev-parse HEAD)
REMOTE_SHA=$(git -C "$CHECKOUT" ls-remote origin "refs/heads/$BRANCH" | awk 'NR==1 {print $1}')

[ -n "$REMOTE_SHA" ] || failed readback remote_branch_missing 5
[ "$LOCAL_SHA" = "$REMOTE_SHA" ] || failed readback sha_mismatch 5

printf 'WIKI_PUSH SUCCESS branch=%s sha=%s\n' "$BRANCH" "$LOCAL_SHA"
