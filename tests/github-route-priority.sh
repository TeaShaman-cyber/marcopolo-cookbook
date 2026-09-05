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

grep -Fq 'Classify the governed push failure before choosing any alternate mutation route.' "$RUNBOOK" || fail "fallback is not gated by failure classification"
grep -Fq 'Non-fast-forward, branch protection, hook/policy rejection, invalid refspec, or wrong remote' "$RUNBOOK" || fail "semantic and policy push failures are not stop conditions"
grep -Fq 'Prefer native GitHub or public exact-ref readback' "$RUNBOOK" || fail "independent readback is not primary"
if grep -Fq 'A safe diagnostic is `git push --dry-run` under both profiles.' "$WRAPPER"; then
  fail "wrapper still prescribes the default-profile write probe"
fi
grep -Fq 'Historical paired diagnostic evidence' "$WRAPPER" || fail "historical default-profile evidence is not clearly separated from current procedure"
grep -Fq 'The checked-in evidence establishes bounded credential-context observations, not repeated same-operation A/B trials.' "$RUNBOOK" || fail "credential-route evidence claim remains over-broad"

EARLY_ROUTING="$(sed -n '/### Established routing/,/## 6\. Governed smart-HTTP first/p' "$RUNBOOK")"
grep -Fq 'classified transport/auth availability failure' <<<"$EARLY_ROUTING" || fail "established routing summary lacks classified fallback gate"
if grep -Fq -- '-> GitHub API / Git Database / contents-ref only after governed transport is observed unavailable' <<<"$EARLY_ROUTING"; then
  fail "established routing diagram still permits generic unavailability fallback"
fi
if grep -Fq 'only after the governed smart-HTTP route is observed unavailable, or when' <<<"$EARLY_ROUTING"; then
  fail "established routing prose still permits generic unavailability fallback"
fi

printf 'GITHUB_ROUTE_PRIORITY PASS\n'
