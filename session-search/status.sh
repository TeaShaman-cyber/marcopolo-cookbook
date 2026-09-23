#!/bin/sh
set -eu

TOOL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RUNTIME_ENV=${SESSION_SEARCH_RUNTIME_ENV:-$TOOL_DIR/runtime.env}

. "$TOOL_DIR/runtime-bindings.sh"
session_search_load_runtime "$RUNTIME_ENV"

exec python3 "$TOOL_DIR/status.py" "$@"
