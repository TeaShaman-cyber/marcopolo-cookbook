#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$ROOT/session-search"
REF=""

if [[ "${1:-}" == "--ref" ]]; then
	[[ $# -ge 2 ]] || {
		echo 'usage: materialize-runtime.sh [--ref REF] [TARGET]' >&2
		exit 64
	}
	REF=$2
	shift 2
fi

TARGET="${1:-/workspace/tools/session-search}"
[[ $# -le 1 ]] || {
	echo 'usage: materialize-runtime.sh [--ref REF] [TARGET]' >&2
	exit 64
}
FILES=(README.md search.sh acceptance.sh status.sh status.py runtime-bindings.sh local-projection.sh local_projection.py)

mkdir -p "$TARGET"
STAGE=$(mktemp -d "$TARGET/.materialize.XXXXXX")
trap 'rm -rf "$STAGE"' EXIT

if [[ -n "$REF" ]]; then
	REF_HEAD=$(git -C "$ROOT" rev-parse --verify "$REF^{commit}") || {
		echo "SESSION_SEARCH MATERIALIZE BLOCKED: canonical ref unavailable: $REF" >&2
		exit 69
	}
	for name in "${FILES[@]}"; do
		git -C "$ROOT" show "$REF:session-search/$name" >"$STAGE/$name" || {
			echo "SESSION_SEARCH MATERIALIZE BLOCKED: helper missing at $REF: $name" >&2
			exit 69
		}
	done
	SOURCE_LABEL="$REF@$REF_HEAD"
else
	for name in "${FILES[@]}"; do
		cp "$SOURCE/$name" "$STAGE/$name"
	done
	SOURCE_LABEL="working-tree"
fi

chmod 0755 "$STAGE/search.sh" "$STAGE/acceptance.sh" "$STAGE/status.sh" "$STAGE/local-projection.sh"
chmod 0644 "$STAGE/README.md" "$STAGE/status.py" "$STAGE/runtime-bindings.sh" "$STAGE/local_projection.py"

for name in "${FILES[@]}"; do
	mv -f "$STAGE/$name" "$TARGET/$name"
done

for name in "${FILES[@]}"; do
	if [[ -n "$REF" ]]; then
		git -C "$ROOT" show "$REF:session-search/$name" | cmp -s - "$TARGET/$name"
	else
		cmp -s "$SOURCE/$name" "$TARGET/$name"
	fi
done

printf 'SESSION_SEARCH_RUNTIME_MATERIALIZED source=%s target=%s\n' "$SOURCE_LABEL" "$TARGET"
sha256sum "${FILES[@]/#/$TARGET/}"
