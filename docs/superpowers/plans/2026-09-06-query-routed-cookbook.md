# Query-Routed Cookbook Implementation Plan

Goal: prove that task labels can compile a small, exact cookbook context packet without introducing another large routing DSL.

Spec: `docs/superpowers/specs/2026-09-06-query-routed-cookbook-design.md`

## Current accepted model

```text
policies = reusable exact Markdown section bundles
routes   = exact labels -> include policies + own sections
```

Selection:

```text
0 matches  -> UNKNOWN
1 match    -> compile
2+ matches -> ROUTE_AMBIGUOUS
```

Explicitly absent from v0.1:

- priority;
- route inheritance;
- route-ID inhibition;
- abstract routes;
- semantic matching;
- dynamic telemetry weights.

## Completed checkpoints

### Task 1 — structural validation

Implemented fail-closed validation for schema, IDs, labels, section paths, file existence, exact headings, duplicate references, and bounded repository paths.

### Task 2 — deterministic route selection

Implemented exact label matching and explicit ambiguity failure.

The earlier priority/inheritance/inhibition experiment was later rejected as unnecessary complexity.

### Task 3 — bounded context compilation

Implemented exact Markdown extraction, stable section de-duplication, hard section budget, explicit UNKNOWN packets, and executable fixtures.

### Review simplification checkpoint

Feynman review and Codex review identified four problems in the earlier model:

1. inheritance-only routes accidentally participated in matching;
2. fenced code could be mistaken for Markdown headings;
3. public compilation did not enforce complete validation first;
4. inhibition edge cases could disguise configuration errors as UNKNOWN.

The accepted response is architectural simplification, not adding more routing machinery:

- reusable content moved to `policies`;
- routes now only select tasks;
- priority, inheritance, and inhibition removed;
- `compile_context()` validates the whole manifest before selection;
- Markdown heading recognition tracks fenced code.

## Task 4 — bind a few real cookbook sections

Scope remains intentionally small.

Start with real routes for:

- structured editing through `workspace_shell`;
- GitHub read operations;
- GitHub mutation through governed write route;
- postcondition/readback policy shared where appropriate.

TDD steps:

1. add fixture expectations using exact current Markdown headings;
2. verify RED against the empty canonical manifest;
3. add only the required policies and routes to `context-routing/routes.json`;
4. validate every reference against repository Markdown;
5. compile sample packets and check ordered section identities;
6. verify UNKNOWN for an unrelated task;
7. run full repository regressions.

Do not add a general-purpose route hierarchy or broad fallback matcher.

## Task 5 — thin CLI and acceptance surface

Add a minimal CLI that accepts already-classified exact labels and prints normalized JSON.

Example intent:

```text
context-router --labels-json '{"surface":"workspace_shell","operation":"structured_edit"}'
```

The CLI must not perform LLM classification, semantic search, or actions.

Acceptance checks:

- known task -> MATCHED with bounded exact sections;
- unrelated task -> UNKNOWN;
- two matching routes -> ROUTE_AMBIGUOUS;
- stale unselected reference -> hard failure;
- fenced-code heading-like text -> ignored;
- context overflow -> `CONTEXT_BUDGET_EXCEEDED` with no partial packet.

## Final research checkpoint

Before any merge decision:

1. run full tests, Ruff, bootstrap/wiki regressions, and `git diff --check`;
2. request Codex review on the final prototype;
3. independently read back the PR head and review findings;
4. compare context packet size/clarity against simply reading the relevant cookbook sections manually;
5. decide whether the router genuinely improves retrieval or merely relocates complexity.

## Deferred research

Only after v0.1 proves useful:

```text
instrument route decisions
-> collect outcome telemetry
-> build rebuildable statistics
-> test bounded dynamic weights
```

Prometheus/Mimir may be useful telemetry substrates later, but canonical routing state remains in Git/JSON/Markdown and hard authority constraints remain static.
