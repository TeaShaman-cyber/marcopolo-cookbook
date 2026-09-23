#!/bin/sh
set -eu

TOOL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RUNTIME_ENV=${SESSION_SEARCH_RUNTIME_ENV:-$TOOL_DIR/runtime.env}

# Local control-plane binding only; corpus artifacts remain authority.
. "$TOOL_DIR/runtime-bindings.sh"
session_search_load_runtime "$RUNTIME_ENV"

"$TOOL_DIR/status.sh" --check-search || exit $?

ROOT=${SESSION_SEARCH_IMPLEMENTATION_ROOT:-/workspace/theseus-session-search-lab}
CORPUS=${SESSION_SEARCH_CORPUS:-}
if [ -z "$CORPUS" ]; then
	echo "SESSION_SEARCH BLOCKED: CORPUS_LOCATION_UNRESOLVED; set SESSION_SEARCH_CORPUS or configure $RUNTIME_ENV" >&2
	exit 69
fi

if [ ! -f "$ROOT/session_search/search.py" ]; then
	echo "SESSION_SEARCH BLOCKED: search implementation unavailable: $ROOT" >&2
	exit 69
fi
if [ ! -r "$CORPUS/corpus.sqlite3" ] || [ ! -d "$CORPUS/ledger/accepted" ]; then
	echo "SESSION_SEARCH BLOCKED: cumulative corpus unavailable: $CORPUS" >&2
	exit 69
fi

for arg in "$@"; do
	case "$arg" in
	--db | --corpus | --db=* | --corpus=*)
		echo "SESSION_SEARCH BLOCKED: wrapper owns corpus selection; invoke python module directly for alternate projections" >&2
		exit 64
		;;
	esac
done

SEARCH_CORPUS=$CORPUS
if LOCAL_CORPUS=$("$TOOL_DIR/local-projection.sh" --path); then
	SEARCH_CORPUS=$LOCAL_CORPUS
fi

cd "$ROOT"
exec python3 -m session_search.search "$@" --corpus "$SEARCH_CORPUS"
