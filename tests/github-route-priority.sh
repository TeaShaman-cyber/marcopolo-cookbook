#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNBOOK="$ROOT/marcopolo/README.md"
WRAPPER="$ROOT/README-github-wrapper.md"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

grep -Fq 'GitHub remote WRITE' "$RUNBOOK" || fail "missing remote write route"
grep -Fq 'GH_CONFIG_DIR=/workspace/.config/gh-write' "$RUNBOOK" || fail "missing explicit gh-write identity"
grep -Fq 'Do not spend the first write attempt on the default/read profile.' "$RUNBOOK" || fail "default write attempt is not explicitly forbidden"
grep -Fq 'Governed smart-HTTP is the primary branch-publication route when Git transport is appropriate.' "$RUNBOOK" || fail "governed smart-HTTP is not primary"
grep -Fq 'Use GitHub API / Git Database / contents-ref publication only after the governed smart-HTTP route is observed unavailable' "$RUNBOOK" || fail "API fallback is not bounded behind governed transport failure"

grep -Fq 'write -> explicit gh-write first' "$WRAPPER" || fail "wrapper route does not select gh-write first"
grep -Fq 'never probe a GitHub write with the default/read profile first' "$WRAPPER" || fail "wrapper does not forbid default write probe"
grep -Fq 'API publication is a fallback after governed Git transport fails' "$WRAPPER" || fail "wrapper does not bound API fallback"

printf 'GITHUB_ROUTE_PRIORITY PASS\n'
