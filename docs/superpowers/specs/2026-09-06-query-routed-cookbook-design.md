# Query-Routed Cookbook Design

Status: accepted research design, simplified after Feynman review and Codex checkpoint review.

## Research question

Can the MarcoPolo cookbook behave as query-addressable operational memory without turning its routing layer into another large prompt or DSL?

The v0.1 test is deliberately small:

```text
task labels
  -> exact route match
  -> reusable policies + exact Markdown sections
  -> bounded context packet
```

Markdown remains the canonical human-readable operational content.

## Feynman invariant

A route should be explainable as:

> For this exact kind of task, include these reusable policies and these exact cookbook sections.

If the schema needs more machinery than that, the machinery must earn its place with evidence.

## v0.1 data model

There are only two routing concepts.

### Policy

A named reusable bundle of exact Markdown section references.

```json
{
  "verification": {
    "sections": [
      {"path": "marcopolo/README.md", "heading": "## Verification"}
    ]
  }
}
```

Policies do not match tasks and do not inherit other policies in v0.1.

### Route

An exact label matcher plus optional policy includes and route-local sections.

```json
{
  "id": "workspace-shell.structured-edit",
  "match": {
    "surface": "workspace_shell",
    "operation": "structured_edit"
  },
  "include": ["verification"],
  "sections": [
    {"path": "marcopolo/README.md", "heading": "## Execution language routing"}
  ]
}
```

`match` values are exact strings. Every key must match. Empty route matchers are invalid.

## Selection semantics

```text
0 matching routes -> UNKNOWN
1 matching route  -> compile it
2+ matching routes -> ROUTE_AMBIGUOUS
```

There is no numeric priority in v0.1.
There is no route inheritance in v0.1.
There is no route-ID inhibition in v0.1.
There are no abstract or non-selectable routes because reusable content lives in policies instead.

The fallback route ID is output metadata for an UNKNOWN packet; it is not a selectable route node.

## Compilation semantics

`compile_context()` is the public safety boundary and MUST validate the complete manifest before route selection.

Compilation order:

```text
validate complete manifest
-> select one exact route or UNKNOWN
-> expand included policies in declared order
-> append route-local sections
-> stable de-duplicate section references
-> enforce max_sections
-> extract exact Markdown sections
-> emit packet
```

A stale reference anywhere in the manifest is a hard failure, even if the stale route or policy would not have been selected for the current task.

## Markdown references

A section reference is:

```json
{"path": "marcopolo/README.md", "heading": "## Exact heading"}
```

Validation and extraction MUST:

- keep paths inside repository root;
- require the file to exist;
- require the heading to exist exactly once as a real Markdown heading;
- ignore heading-looking text inside fenced code blocks;
- include child subsections;
- stop before the next real heading whose level is equal to or higher than the selected heading.

No Markdown dependency is required for the prototype; a bounded deterministic parser is sufficient for these rules.

## Context budget

`defaults.max_sections` is a hard limit after policy expansion and de-duplication.

Overflow returns `CONTEXT_BUDGET_EXCEEDED` before any partial packet is returned.

## Packet

Matched result:

```json
{
  "schema_version": "cookbook-context-v0.1",
  "route_state": "MATCHED",
  "route_id": "workspace-shell.structured-edit",
  "labels": {
    "operation": "structured_edit",
    "surface": "workspace_shell"
  },
  "sections": []
}
```

Miss:

```json
{
  "schema_version": "cookbook-context-v0.1",
  "route_state": "UNKNOWN",
  "route_id": "default.unknown",
  "labels": {},
  "sections": []
}
```

UNKNOWN means no explicit route matched. It must never hide ambiguity or invalid configuration.

## Authority boundary

Routing selects context. It does not grant permission to act.

Operational authority remains governed by the cookbook and runtime controls. A routing result cannot make an otherwise forbidden write route legal.

## Why the earlier model was rejected

The first prototype used route priority, route inheritance, and route-ID inhibition. Review showed that these concepts made reusable content and task selection share one abstraction. That forced inheritance-only routes to carry fake non-matching labels and created avoidable edge cases.

The simplified model separates:

```text
policy = what reusable context to include
route  = when to include it
```

This directly answers the research question with less machinery.

## Deferred lanes

Not part of v0.1:

- semantic or embedding-based route selection;
- LLM label extraction as part of router correctness;
- dynamic route weights;
- Prometheus/Mimir telemetry feedback;
- generalized inhibition or route priorities;
- nested policy composition;
- automatic operation execution.

If later evidence justifies a model-facing routing serialization, it should follow the same lesson as compact tool-call formats such as DSML: keep the canonical machine schema rich enough for the system, but project only a tiny deterministic representation to the model.

Telemetry may later adjust ranking only among already-permitted alternatives. It must never override authority or safety constraints.

## v0.1 success criteria

- same labels + same manifest -> same result;
- exactly zero matches -> UNKNOWN;
- more than one match -> deterministic ambiguity failure;
- reusable policies do not participate in matching;
- stale references fail before evaluation;
- fenced code cannot truncate or create headings;
- context budget is hard and produces no partial packet;
- existing Markdown remains canonical;
- the routing layer remains substantially smaller and simpler than the content it routes.
