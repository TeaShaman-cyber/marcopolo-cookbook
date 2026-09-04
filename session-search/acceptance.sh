#!/usr/bin/env sh
set -eu

ROOT=/workspace/theseus-session-search-lab
RUNTIME_ENV=/workspace/tools/session-search/runtime.env
MODE=READ_ONLY_DEFAULT
INGEST_PATH=
QUERY=session

usage() {
  cat <<'EOF'
Usage: acceptance.sh [--query TEXT] [--ingest PATH]

Default mode is read-only against the live corpus. It verifies health,
performs global and session-scoped search, and rebuilds a temporary copy
from durable evidence. --ingest explicitly enables one idempotent ingest
before the checks.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --query)
      [ "$#" -ge 2 ] || { echo 'SESSION_SEARCH BLOCKED: QUERY_UNRESOLVED' >&2; exit 64; }
      QUERY=$2
      shift 2
      ;;
    --ingest)
      [ "$#" -ge 2 ] || { echo 'SESSION_SEARCH BLOCKED: INGEST_PATH_UNRESOLVED' >&2; exit 64; }
      MODE=EXPLICIT_INGEST
      INGEST_PATH=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "SESSION_SEARCH BLOCKED: UNKNOWN_ARGUMENT: $1" >&2
      exit 64
      ;;
  esac
done

if [ -z "${SESSION_SEARCH_CORPUS:-}" ] && [ -r "$RUNTIME_ENV" ]; then
  . "$RUNTIME_ENV"
fi
CORPUS=${SESSION_SEARCH_CORPUS:-}
if [ -z "$CORPUS" ]; then
  echo 'SESSION_SEARCH BLOCKED: CORPUS_LOCATION_UNRESOLVED' >&2
  exit 69
fi
if [ ! -d "$ROOT" ] || [ ! -r "$CORPUS/corpus.sqlite3" ] || [ ! -d "$CORPUS/ledger/accepted" ]; then
  echo 'SESSION_SEARCH BLOCKED: CORPUS_UNAVAILABLE' >&2
  exit 69
fi
if [ "$MODE" = EXPLICIT_INGEST ]; then
  [ -n "$INGEST_PATH" ] || { echo 'SESSION_SEARCH BLOCKED: INGEST_PATH_UNRESOLVED' >&2; exit 64; }
  [ -r "$INGEST_PATH" ] || { echo 'SESSION_SEARCH BLOCKED: INGEST_PATH_UNREADABLE' >&2; exit 66; }
fi

cd "$ROOT"
printf '%s\n' "SESSION_SEARCH_ACCEPTANCE mode=$MODE"

LIVE_VERIFY=$(python3 -m session_search.corpus verify --corpus "$CORPUS" --json)
printf '%s\n' "$LIVE_VERIFY"

if [ "$MODE" = EXPLICIT_INGEST ]; then
  python3 -m session_search.corpus ingest --corpus "$CORPUS" --json "$INGEST_PATH"
  LIVE_VERIFY=$(python3 -m session_search.corpus verify --corpus "$CORPUS" --json)
  printf '%s\n' "$LIVE_VERIFY"
fi

GLOBAL=$(python3 -m session_search.search "$QUERY" --corpus "$CORPUS" --limit 8 --json)
SESSION_ID=$(printf '%s' "$GLOBAL" | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(rows[0]["session_id"] if rows else "")')
[ -n "$SESSION_ID" ] || { echo 'SESSION_SEARCH BLOCKED: SEARCH_NO_HITS' >&2; exit 70; }
printf '%s\n' "$GLOBAL"
python3 -m session_search.search "$QUERY" --corpus "$CORPUS" --session "$SESSION_ID" --limit 8 --json

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
mkdir -p "$TMP/artifacts" "$TMP/ledger" "$TMP/receipts/ingest" "$TMP/receipts/rebuild" "$TMP/staging"
cp -a "$CORPUS/artifacts/." "$TMP/artifacts/"
cp -a "$CORPUS/ledger/." "$TMP/ledger/"
REBUILD=$(python3 -m session_search.corpus rebuild --corpus "$TMP" --json)
REBUILT_VERIFY=$(python3 -m session_search.corpus verify --corpus "$TMP" --json)
printf '%s\n' "$REBUILD"
printf '%s\n' "$REBUILT_VERIFY"

printf '%s\n%s\n' "$LIVE_VERIFY" "$REBUILT_VERIFY" | python3 -c '
import json,sys
lines=[line for line in sys.stdin.read().splitlines() if line.strip()]
live=json.loads(lines[0]); rebuilt=json.loads(lines[1])
keys=("artifacts","sessions","messages","message_sources","payload_pages","fts_rows","sqlite_integrity")
bad={k:(live.get(k),rebuilt.get(k)) for k in keys if live.get(k)!=rebuilt.get(k)}
if bad:
    print("SESSION_SEARCH BLOCKED: REBUILD_MISMATCH", bad, file=sys.stderr)
    raise SystemExit(71)
print("SESSION_SEARCH_ACCEPTANCE PASS")
'
