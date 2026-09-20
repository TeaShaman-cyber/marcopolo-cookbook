#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHECK="$ROOT/git-worktree-currentness.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
REPO="$TMP/repo"
mkdir -p "$REPO"
git -C "$REPO" init -q -b main
git -C "$REPO" config user.name test
git -C "$REPO" config user.email test@example.invalid
printf 'base\n' >"$REPO/state.txt"
git -C "$REPO" add state.txt
git -C "$REPO" commit -q -m base
git -C "$REPO" update-ref refs/remotes/origin/main HEAD

"$CHECK" "$REPO" origin/main | grep -Fq 'WORKTREE_CURRENTNESS VERIFIED'

git -C "$REPO" switch -q -c research/stale
git -C "$REPO" switch -q main
printf 'current\n' >>"$REPO/state.txt"
git -C "$REPO" commit -q -am current
git -C "$REPO" update-ref refs/remotes/origin/main HEAD
git -C "$REPO" switch -q research/stale

set +e
OUTPUT="$($CHECK "$REPO" origin/main 2>&1)"
STATUS=$?
set -e
[[ "$STATUS" -eq 3 ]]
grep -Fq 'WORKTREE_CURRENTNESS BLOCKED reason=head_mismatch' <<<"$OUTPUT"

printf 'local edit\n' >>"$REPO/state.txt"
git -C "$REPO" update-ref refs/remotes/origin/main HEAD
set +e
OUTPUT="$($CHECK "$REPO" origin/main 2>&1)"
STATUS=$?
set -e
[[ "$STATUS" -eq 4 ]]
grep -Fq 'WORKTREE_CURRENTNESS BLOCKED reason=dirty_worktree' <<<"$OUTPUT"

printf 'PASS git-worktree-currentness\n'
