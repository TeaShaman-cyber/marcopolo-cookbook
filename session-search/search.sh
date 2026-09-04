#!/usr/bin/env sh
set -eu

ROOT=/workspace/theseus-session-search-lab
RUNTIME_ENV=/workspace/tools/session-search/runtime.env

if [ -z "${SESSION_SEARCH_CORPUS:-}" ] && [ -r "$RUNTIME_ENV" ]; then
  # Local control-plane binding only; corpus artifacts remain authority.
  . "$RUNTIME_ENV"
fi

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
    --db|--corpus|--db=*|--corpus=*)
      echo "SESSION_SEARCH BLOCKED: wrapper owns corpus selection; invoke python module directly for alternate projections" >&2
      exit 64
      ;;
  esac
done

cd "$ROOT"
exec python3 -m session_search.search "$@" --corpus "$CORPUS"
