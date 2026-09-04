#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
version=$(./bin/mcpjam --version)
[ "$version" = "5.6.0" ]
./bin/mcpjam server probe --help >/dev/null
./bin/mcpjam skills --help >/dev/null
printf 'PASS: mcpjam-cli %s wrapper, probe, and skills commands available\n' "$version"
