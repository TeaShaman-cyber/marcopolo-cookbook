# Scientific Verifier Stand Design

**Issue:** `TeaShaman-cyber/marcopolo-cookbook#43`

## Purpose

Provide a small reproducible scientific-verification workbench inside MarcoPolo so exact repository evidence, deterministic projection, local mathematical checks, and independent Wolfram witnesses can run in one operational runtime.

The immediate failure mode is model-mediated glue: a source file is read through one tool/runtime, a model manually reconstructs relationships, and a different runtime checks the reconstruction. That is useful for exploration but is not deterministic verification.

The stand therefore enforces this rule:

```text
source bytes -> typed projection -> verifier result
```

must be machine-produced end to end. An LLM may propose a hypothesis or choose what check to run, but it must not invent or repair typed verifier input after reading the source. If deterministic projection cannot establish a required relation, the result is `UNOBSERVABLE_ROUTING`.

## Scope

Initial scope is deliberately small:

- exact GitHub repository/commit/path snapshots acquired inside MarcoPolo;
- deterministic projection adapters producing canonical JSON plus SHA-256;
- local Python checks using NumPy, NetworkX, SymPy, and SciPy where each library is appropriate;
- independent Wolfram checks through the existing repo-managed `mcporter` route;
- durable receipts containing exact inputs, runtime versions, outputs, and comparison status.

Not in initial scope:

- general theorem proving;
- prose-level semantic understanding by an LLM as verifier input;
- a graph database, hosted service, notebook server, or background daemon;
- matplotlib or visualization dependencies;
- changing system Python, system Node, existing mcporter pins, credentials, or platform-owned runtimes;
- making Wolfram mandatory for the local baseline;
- automatically promoting verifier findings to authority or acceptance decisions.

## Relationship to existing components

`mcporter/` remains the canonical MCP client workbench. This component consumes its wrapper rather than duplicating or replacing it.

Cookbook issue #4 remains the symbolic-compute fallback routing experiment. The scientific verifier stand may use an accepted local symbolic fallback in degraded mode later, but it does not redefine #4.

Theseus Research #42 remains the scientific experiment evaluating whether machine-readable workflow contracts add useful defect-detection power. This cookbook component supplies reproducible infrastructure; it does not decide the research conclusion.

## Component layout

```text
scientific-verifier/
  README.md
  runtime/
    python.env
    requirements.lock
  bin/
    scientific-verifier
  scripts/
    install-runtime.sh
    ensure-runtime.sh
    snapshot-github.sh
  lib/
    projection.py
    verify.py
    receipt.py
    wolfram.py
  adapters/
    README.md
    explicit-contract-v1.py
    superpowers-plan-v1.py
  canaries/
    graph-order.json
    transport-boundary.json
    symbolic-algebra.json
    numeric-check.json
  tests/
    acceptance.sh
    test_projection.py
    test_verify.py
    test_receipt.py
    test_runtime.py
```

Generated virtual environments, caches, downloaded wheels, traces, and receipts are not committed as canonical source.

## Runtime design

System Python is not modified.

Canonical runtime state is:

```text
runtime/python.env
runtime/requirements.lock
scripts/install-runtime.sh
scripts/ensure-runtime.sh
```

`python.env` records the supported Python major/minor contract and a bundle identifier. `requirements.lock` contains exact transitive package versions and package hashes suitable for `pip --require-hashes` installation.

The initial direct scientific dependencies are:

```text
numpy
networkx
sympy
scipy
```

Exact versions are selected during implementation by a compatibility probe against the MarcoPolo Python runtime, then frozen in the lock file. No package is silently upgraded.

Runtime materialization occurs under an ephemeral local path such as:

```text
/tmp/marcopolo-scientific-verifier-<uid>/<bundle-id>/
```

The installer builds into a staging directory, verifies Python and package versions, then atomically promotes the completed runtime. `ensure-runtime.sh` uses locking so concurrent callers cannot observe a partially built environment.

NFS-hosted virtualenvs under `/workspace` are explicitly avoided.

## Source snapshot boundary

A verifier run begins from an exact source identity:

```json
{
  "repository": "owner/repo",
  "commit": "40-hex-sha",
  "path": "path/in/repository"
}
```

`snapshot-github.sh` runs through the existing governed MarcoPolo GitHub read profile and writes the exact bytes to a run directory together with a source receipt containing:

- repository;
- exact commit;
- path;
- blob/content identity when available;
- source SHA-256;
- retrieval timestamp and route.

The snapshot is local verifier input. The verifier never consumes text copied from a ChatGPT connector response.

## Projection contract

Projection adapters are deterministic programs. Their output has a common envelope:

```json
{
  "schema": "theseus.scientific-verifier.projection.v1",
  "adapter": {
    "name": "explicit-contract-v1",
    "version": "1"
  },
  "source": {
    "repository": "owner/repo",
    "commit": "...",
    "path": "...",
    "sha256": "..."
  },
  "relations": [],
  "coverage": {
    "status": "COMPLETE_FOR_ADAPTER_SCOPE",
    "unobservable": []
  }
}
```

Projection JSON is canonicalized before hashing. The projection SHA-256 is a required input binding for every verifier receipt.

### Adapter rule

An adapter may emit a typed relation only when that relation follows from syntax or other deterministic evidence covered by the adapter contract.

It must never call an LLM to fill missing semantics.

If a required relationship cannot be derived, the adapter emits a concrete coverage gap. The router/verifier must propagate that as `UNOBSERVABLE_AT_THIS_LAYER` or `UNOBSERVABLE_ROUTING` rather than treating absence as safety.

### Initial adapters

`explicit-contract-v1` handles already-machine-readable JSON contracts. This is the preferred path and the future source of truth for skills/workflows whose Markdown is only a human projection.

`superpowers-plan-v1` is a bounded legacy adapter for explicit, mechanically recognizable plan structures only. It may extract headings, declared commands, explicit artifact names, and explicit structured markers, but it must not infer semantic producer/consumer/provenance links from natural-language similarity. Ambiguous legacy prose therefore remains unobservable.

This restriction is intentional: a low-recall deterministic projection is acceptable; hidden manual semantic completion is not.

## Applicability routing

The verifier consumes typed relations, not prose. A thin router maps relation presence to already-defined invariant families, for example:

```text
ordered_events / route_transitions   -> PHASE
production_contracts / RED required  -> TDD
runtime_bindings                     -> RUNTIME_BINDING
transports                            -> TRANSPORT_BOUNDARY
claims / evidence_bindings           -> CLAIM_PROVENANCE
requires_authority                   -> AUTHORITY
```

Output includes:

```json
{
  "applicable": [],
  "checked": [],
  "not_evaluated": []
}
```

Plan-level `SAFE_WITHIN_SCOPE` is prohibited while an applicable declared invariant remains unevaluated.

## Local verifier layer

The local verifier is required and remains usable without Wolfram.

Library roles are intentionally narrow:

- Python stdlib: canonical JSON, hashing, finite-set relations, receipt generation;
- NetworkX: graph reachability, DAG/order, paths, cycles, bottleneck/cut-style counterexamples where useful;
- SymPy: exact symbolic identities, algebraic simplification, exact rational/matrix checks;
- NumPy: explicit finite numeric/vector/matrix canaries where floating-point computation is part of the declared contract;
- SciPy: scientific/numerical algorithms only when the check genuinely requires them; it is not imported merely to make the stack look scientific.

Every failed invariant returns a concrete counterexample or witness. No aggregate quality score is required.

Primary states remain:

```text
SAFE_WITHIN_SCOPE
UNSAFE
UNOBSERVABLE_AT_THIS_LAYER
```

## Independent Wolfram witness

The optional independent witness uses:

```text
/workspace/tools/mcporter/bin/mcporter
```

and the existing non-secret Wolfram server definition.

The Wolfram expression must be independently authored from the mathematical property, not generated by translating the Python verifier line by line.

Comparison states:

```text
AGREEMENT
FORMAL_CONFLICT
DEGRADED_EXTERNAL_VERIFIER
```

Rules:

- local Python result remains available when Wolfram transport is unavailable;
- Wolfram unavailability never converts a local result to success or failure;
- disagreement produces `FORMAL_CONFLICT` and blocks promotion of the formal claim until investigated;
- transport/auth/service failures are reported as verifier-route evidence, not scientific conclusions.

## Receipt contract

Every run writes one canonical JSON receipt containing at least:

```text
source identity + source SHA-256
projection adapter + version
projection SHA-256
Python version
NumPy / NetworkX / SymPy / SciPy versions
local invariant results + counterexamples
Wolfram route/version evidence when invoked
Wolfram results or degraded status
comparison disposition
run timestamp
```

A receipt may claim only what its bound source/projection/runtime established. A successful command without exact bindings is not verification evidence.

## Initial acceptance canaries

The first implementation earns promotion only with small deterministic canaries:

1. **Graph/order:** producer-before-consumer good/bad fixtures, checked locally with NetworkX and independently in Wolfram.
2. **Transport boundary:** exact round-trip/injectivity good/bad fixtures for structured versus lossy transport.
3. **Symbolic:** one exact algebraic identity and one deliberately false identity, checked with SymPy and Wolfram.
4. **Numeric/scientific:** one bounded deterministic numerical property that exercises NumPy/SciPy with an explicit tolerance and independently specified expected condition.
5. **Projection coverage:** explicit typed contract routes successfully; ambiguous legacy prose produces `UNOBSERVABLE_ROUTING` without LLM repair.
6. **Conflict canary:** a deliberately altered independent-witness expectation yields `FORMAL_CONFLICT` rather than majority voting.

Acceptance must record exact package/runtime versions and projection hashes.

## Anti-bureaucracy constraint

This stand is an optional verifier route, not a mandatory form to fill out for every task.

A workflow uses it when at least one of these is true:

- the plan already has a typed contract;
- a deterministic adapter can derive relevant typed relations;
- a scientific or formal claim benefits from an independent computation;
- a representation/provenance/phase boundary is consequential enough to justify a preflight.

If a cheap ordinary test or linter already establishes the property more directly, use that instead.

The method fails its design goal if adding a check requires a modeler to manually encode the expected defect, or if the schema approaches the complexity of the underlying repository.

## Failure semantics

```text
SOURCE_SNAPSHOT_FAILED
  exact source input was not acquired; no verifier conclusion

PROJECTION_FAILED
  deterministic adapter malfunctioned; no verifier conclusion

UNOBSERVABLE_ROUTING
  source was acquired, but required typed applicability could not be derived

UNSAFE
  a represented invariant has a concrete counterexample

FORMAL_CONFLICT
  independent valid verifier routes disagree

DEGRADED_EXTERNAL_VERIFIER
  local result exists, external witness unavailable or transport-failed
```

No failure state silently triggers a route mutation, dependency upgrade, or authority change.

## Verification and promotion

Implementation is accepted only after:

- isolated runtime rebuild from canonical lock succeeds;
- local acceptance suite passes from a fresh runtime;
- mcporter acceptance remains green;
- at least one real Wolfram cross-check returns agreement;
- deliberate bad fixtures produce the expected counterexamples;
- deliberate witness disagreement produces `FORMAL_CONFLICT`;
- exact Git remote readback confirms the committed design/implementation state.

Promotion into normal project workflow is a separate decision from proving the stand works.

## Rollback

Rollback removes the versioned `scientific-verifier/` component and its workflow references. Ephemeral `/tmp` runtime/cache state can be deleted independently. No system Python, system Node, credential store, or existing mcporter configuration needs restoration.
