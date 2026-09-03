#!/usr/bin/env sh
set -eu
ROOT=/workspace/theseus-session-search-lab
DB=/workspace/research/barn-session-search/index/session-search-full.sqlite3
if [ ! -f "$ROOT/session_search/search.py" ] || [ ! -f "$DB" ]; then
  echo 'SESSION_SEARCH BLOCKED: portable search or corpus unavailable' >&2
  exit 69
fi
cd "$ROOT"
exec python3 -m session_search.search "$@" --db "$DB"
