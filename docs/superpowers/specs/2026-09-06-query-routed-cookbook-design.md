# Query-Routed Cookbook Design

## Status

Research design for issue #24. This document defines the first bounded experiment only. It does not convert the whole cookbook, change cookbook authority, or install a new runtime router.

## Problem

The cookbook can contain the correct operational rule while an agent still fails to apply it because the rule is spread across multiple sections or is not salient for the current task.

The failure chain is therefore:

```text
information exists
!= information is retrieved
!= information is salient
!= information affects execution
```

The shell execution-language work is the motivating example: relevant guidance already existed, but it was distributed across sections, so the operational route did not consistently influence execution.

## Research question

Can the cookbook act as **query-addressable operational memory** by deterministically compiling a small task-specific context packet from structured task labels, inheritance, inhibition, and an explicit fallback route?

The intended model is analogous to Prometheus / Alertmanager routing:

```text
task
  -> labels
  -> route matching
  -> inherited policy
  -> inhibition
  -> exact section references
  -> bounded context packet
```

## Design principles

### 1. Context is a compiled execution view

The persistent corpus is not itself the execution context.

```text
cookbook corpus
    -> routed query
    -> bounded section set
    -> compiled context packet
```

A task should receive only the smallest operational working set needed for the current decision.

### 2. Markdown remains canonical content in the first lane

The first prototype MUST NOT duplicate rule bodies into JSON/YAML.

The routing manifest may contain:

- stable route identifiers;
- task matchers;
- inheritance relationships;
- inhibition relationships;
- exact references to Markdown sections;
- routing metadata needed to construct a packet.

The manifest must not contain an alternate prose copy of the rule.

```text
manifest = routing/index state
Markdown = operational content authority
```

If this experiment succeeds, later research may evaluate JSON-first rule state with generated Markdown projections. That is explicitly outside this first lane.

### 3. Deterministic first, semantic later

The first router uses exact structured labels only. No embeddings, LLM classification, vector search, BM25, fuzzy matching, or learned ranking is required.

Given the same manifest version and the same normalized labels, routing output must be byte-for-byte deterministic after canonical serialization.

### 4. Miss means UNKNOWN, not guessed route

If no explicit route matches, the router returns an explicit fallback packet with:

```text
route_state = UNKNOWN
```

It must not silently choose the nearest-looking route.

### 5. Routing does not grant authority

A route determines which guidance becomes salient. It does not alter GitHub write authority, runtime permissions, credential boundaries, or any other operational authorization.

Existing authority rules remain canonical in their current cookbook sections.

## Initial scope

The first prototype covers only three existing operational families:

1. `workspace_shell` execution-language selection;
2. GitHub READ/WRITE authority routing;
3. postcondition / readback verification.

These are deliberately chosen because they exercise inheritance, inhibition, and cross-cutting global invariants without requiring the entire cookbook to be converted.

## Proposed repository shape

```text
context-routing/
  routes.json
  README.md

context-routing.py

tests/
  fixtures/context-routing-v0.1.json
  test_context_routing.py
```

The exact executable location may be adjusted during implementation if an existing repository convention provides a clearer home, but the logical boundaries remain:

- manifest;
- pure deterministic routing core;
- fixture-exact tests;
- human-facing explanation.

## Manifest schema v0.1

Top-level shape:

```json
{
  "schema_version": "cookbook-routing-v0.1",
  "defaults": {
    "max_sections": 4,
    "fallback_route": "default.unknown"
  },
  "routes": []
}
```

Each route has:

```json
{
  "id": "workspace-shell.structured-edit",
  "priority": 200,
  "match": {
    "surface": ["workspace_shell"],
    "operation": ["structured_edit"]
  },
  "inherits": ["marcopolo.global"],
  "inhibits": ["workspace-shell.inline-complex-shell"],
  "sections": [
    {
      "path": "marcopolo/README.md",
      "heading": "## 1. `/bin/sh` is not Bash"
    },
    {
      "path": "marcopolo/README.md",
      "heading": "## 2. Nested shell quoting and heredocs are a failure domain"
    }
  ]
}
```

### Route identity

`id` is a stable unique string and must not depend on Markdown heading text.

### Labels

Input labels are a flat mapping of normalized strings:

```json
{
  "domain": "marcopolo",
  "surface": "workspace_shell",
  "operation": "structured_edit",
  "mutation": "true"
}
```

For v0.1:

- keys are lowercase ASCII identifiers matching `[a-z0-9_.-]+`;
- values are lowercase strings after caller-side normalization;
- the routing core does not infer missing labels;
- a matcher value is an allow-list; the input value must equal one member exactly;
- absent input labels do not satisfy a matcher.

### Match semantics

All keys inside one route's `match` object are AND conditions.

Values within one key are OR alternatives.

Example:

```json
{
  "match": {
    "surface": ["workspace_shell"],
    "operation": ["structured_edit", "generated_file"]
  }
}
```

means:

```text
surface == workspace_shell
AND
(operation == structured_edit OR operation == generated_file)
```

### Priority

Higher integer priority wins among simultaneously matching routes.

Equal-priority simultaneous matches are a configuration error unless one route is eliminated by inhibition before winner selection.

The router must fail validation for an ambiguous equal-priority fixture rather than relying on manifest order.

## Inheritance

Inheritance is additive and explicit.

A route may inherit zero or more parent route IDs. Parents contribute section references and inherited route metadata but do not contribute their matchers.

Example:

```text
marcopolo.global
    sections: runtime boundary, postcondition rule

workspace-shell.structured-edit
    inherits: marcopolo.global
    sections: shell-language route, quoting rule
```

Compiled section order is deterministic:

1. inherited ancestors from root to leaf;
2. winning route sections;
3. duplicate section references removed while preserving first occurrence.

Inheritance cycles are invalid and must fail manifest validation.

## Inhibition

Inhibition prevents a route from being selected or contributing content when a matching higher-authority route explicitly suppresses it.

For v0.1, inhibition is route-ID based:

```json
"inhibits": ["workspace-shell.inline-complex-shell"]
```

Semantics:

1. evaluate all route matches;
2. construct the set of matching route IDs;
3. apply inhibition edges from matching routes;
4. remove inhibited matches;
5. select the highest-priority remaining route;
6. detect ambiguity if multiple remaining routes share highest priority.

An inhibition target that does not exist is a manifest validation error.

The first prototype does not implement arbitrary Alertmanager-style inhibition expressions. Route-ID inhibition is intentionally smaller and easier to falsify.

## Section references

A section reference is:

```json
{
  "path": "marcopolo/README.md",
  "heading": "## 5. GitHub READ and WRITE authority are asymmetric"
}
```

Validation MUST verify:

- file exists inside repository root;
- heading exists exactly once in the file;
- path does not escape repository root;
- reference is not duplicated within one route after normalization.

The compiler extracts from the exact heading through the line before the next heading at the same or higher Markdown level, or EOF.

A stale/missing/ambiguous heading is a hard validation failure, not a routing miss.

## Context packet v0.1

Normalized packet:

```json
{
  "schema_version": "cookbook-context-v0.1",
  "route_state": "MATCHED",
  "route_id": "workspace-shell.structured-edit",
  "labels": {
    "operation": "structured_edit",
    "surface": "workspace_shell"
  },
  "sections": [
    {
      "path": "marcopolo/README.md",
      "heading": "## 1. `/bin/sh` is not Bash",
      "content": "..."
    }
  ]
}
```

`labels` keys are emitted in sorted order during canonical JSON serialization.

For a miss:

```json
{
  "schema_version": "cookbook-context-v0.1",
  "route_state": "UNKNOWN",
  "route_id": "default.unknown",
  "labels": {"...": "..."},
  "sections": []
}
```

The fallback route may later contain a small generic section set, but the first fixture should begin with an empty UNKNOWN packet so the router cannot hide missing coverage.

## Boundedness

`defaults.max_sections` is a hard cap after inheritance and de-duplication.

If a matched route compiles more sections than the cap, compilation fails with an explicit `CONTEXT_BUDGET_EXCEEDED` result instead of silently truncating.

The first lane budgets by section count, not token count. Token budgeting may be added only after section-count routing is measured.

## First fixture cases

The executable fixture must cover at least:

### A. Structured workspace edit

Input:

```json
{
  "surface": "workspace_shell",
  "operation": "structured_edit"
}
```

Expected route:

```text
workspace-shell.structured-edit
```

Expected salient guidance includes the current sections for:

- `/bin/sh` is not Bash;
- nested quoting/heredoc failure domain;
- global postcondition verification if inherited.

### B. Simple direct CLI operation

Input:

```json
{
  "surface": "workspace_shell",
  "operation": "direct_cli"
}
```

Expected route must not include structured-edit-only shell guidance.

### C. GitHub mutation

Input:

```json
{
  "domain": "github",
  "operation": "mutation"
}
```

Expected guidance must include the existing GitHub READ/WRITE asymmetry and governed write route.

Any direct-connector-write route must be inhibited.

### D. GitHub read

Input:

```json
{
  "domain": "github",
  "operation": "read"
}
```

Expected guidance must not include write-only procedure sections unless inherited as a universal invariant.

### E. Unknown task

Input:

```json
{
  "domain": "unclassified"
}
```

Expected `route_state = UNKNOWN` and no guessed route.

### F. Stale section reference

Manifest references a heading that does not exist.

Expected manifest validation failure.

### G. Ambiguous equal priority

Two non-inhibited matching routes share the highest priority.

Expected validation/evaluation failure rather than manifest-order selection.

### H. Inhibition

A broad unsafe/direct GitHub mutation route and the governed mutation route both match.

Expected governed route survives and unsafe route is inhibited.

### I. Inheritance cycle

A inherits B and B inherits A.

Expected validation failure.

### J. Context budget

A route plus inherited parents exceeds `max_sections`.

Expected `CONTEXT_BUDGET_EXCEEDED` with no partial packet.

## Measurement

The first prototype should measure mechanical properties only:

```text
route_determinism_rate          = 1.0
stale_reference_escape_rate     = 0
ambiguous_route_escape_rate     = 0
inhibition_failure_rate         = 0
unknown_guess_rate              = 0
context_budget_violation_rate   = 0
```

After mechanical conformance passes, a later research lane may measure behavioral outcomes such as whether agents actually make fewer routing mistakes.

## Relationship to the managed Skill

The managed `using-theseus-marcopolo` Skill remains a thin trigger/router candidate.

This experiment does not require modifying or reinstalling that Skill. If the router proves useful, a later integration may let the Skill request a compiled context packet rather than embedding more cookbook content into the Skill body.

Therefore:

```text
Skill = trigger / policy entry
router = deterministic context compiler
cookbook Markdown = operational content
```

Skill selection/auto-load remains runtime-specific and must not be inferred from this experiment.

## Relationship to memory-provider research

The query-routed cookbook and issue #17 solve different layers:

```text
issue #17 memory adapter
    = durable operational observations / recall-retain substrate

issue #24 cookbook router
    = deterministic selection of canonical operational guidance
```

They may later compose, but neither should become authority for the other merely because both produce bounded context.

## Migration strategy if the experiment succeeds

Do not rewrite all 86 Markdown files.

Use incremental coverage:

1. keep existing Markdown unchanged;
2. add route references for high-value failure-prone procedures;
3. validate references in CI/local gate;
4. measure missed/ambiguous routes;
5. only then decide whether some stable rules deserve JSON-first canonical state with generated Markdown projections.

The routing manifest is therefore a **strangler/index layer**, not a migration flag day.

## Security and safety boundary

The router operates on repository-local documentation and normalized task labels.

It must not:

- read secrets;
- infer or elevate authorization;
- execute shell/Git/GitHub operations;
- mutate the cookbook;
- follow paths outside the repository;
- treat route selection as evidence that an action is permitted.

Manifest validation is structural. No semantic “prompt injection” classifier belongs in this first lane.

## Success criteria

The research prototype is successful when:

1. one manifest covers the three initial operational families without copying their rule bodies;
2. fixture-exact routing is deterministic;
3. inheritance and inhibition are independently tested;
4. stale references and ambiguous routes fail closed;
5. UNKNOWN is explicit;
6. compiled packets remain within the configured section budget;
7. existing cookbook tests remain green;
8. no existing Markdown authority or Skill installation changes are required.

## Non-goals

- full cookbook conversion;
- semantic search;
- embeddings;
- LLM-generated labels inside the core router;
- automatic execution of routed guidance;
- replacement of Session Search;
- replacement of the memory-provider adapter;
- promotion of runtime observations into cookbook authority.
