#!/bin/sh
set -eu
MCPORTER=${MCPORTER:-/workspace/tools/mcporter/bin/mcporter}
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TMP=$(mktemp -d /tmp/get-posting-board-auth-XXXXXX)
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
mkdir -p "$TMP/home" "$TMP/xdg"
cat > "$TMP/mcp.json" <<'JSON'
{"mcpServers":{"get-posting-board":{"baseUrl":"https://getpostingboard.dev/mcp","description":"Get Posting Board OAuth preflight"}}}
JSON
set +e
HOME="$TMP/home" XDG_CONFIG_HOME="$TMP/xdg" \
  "$MCPORTER" --config "$TMP/mcp.json" --oauth-timeout 2500 \
  auth get-posting-board --no-browser --json >"$TMP/out" 2>"$TMP/err"
rc=$?
set -e
if [ ! -s "$TMP/out" ]; then
  printf '{"status":"AUTH_START_FAILED","oauth_verified":false,"mcporter_exit":%s}\n' "$rc"
  exit 1
fi
python3 "$HERE/get-posting-board-auth.py" <"$TMP/out"
