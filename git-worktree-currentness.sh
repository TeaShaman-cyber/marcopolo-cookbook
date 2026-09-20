#!/usr/bin/env bash
set -euo pipefail

REPO="${1:-.}"
REF="${2:-origin/main}"

if ! git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	printf 'WORKTREE_CURRENTNESS BLOCKED reason=not_git_worktree repo=%s\n' "$REPO" >&2
	exit 2
fi

if ! REF_SHA="$(git -C "$REPO" rev-parse --verify "$REF^{commit}" 2>/dev/null)"; then
	printf 'WORKTREE_CURRENTNESS UNKNOWN reason=ref_unavailable ref=%s\n' "$REF" >&2
	exit 2
fi

HEAD_SHA="$(git -C "$REPO" rev-parse HEAD)"
BRANCH="$(git -C "$REPO" symbolic-ref --quiet --short HEAD 2>/dev/null || printf 'DETACHED')"

if [[ "$HEAD_SHA" != "$REF_SHA" ]]; then
	printf 'WORKTREE_CURRENTNESS BLOCKED reason=head_mismatch branch=%s head=%s ref=%s ref_sha=%s\n' \
		"$BRANCH" "$HEAD_SHA" "$REF" "$REF_SHA" >&2
	exit 3
fi

if [[ -n "$(git -C "$REPO" status --porcelain)" ]]; then
	printf 'WORKTREE_CURRENTNESS BLOCKED reason=dirty_worktree branch=%s head=%s ref=%s\n' \
		"$BRANCH" "$HEAD_SHA" "$REF" >&2
	exit 4
fi

printf 'WORKTREE_CURRENTNESS VERIFIED branch=%s head=%s ref=%s\n' "$BRANCH" "$HEAD_SHA" "$REF"
