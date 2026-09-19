# MarcoPolo repository lifecycle

This policy defines how repository work moves from an active change to a durable
terminal disposition. It applies to MarcoPolo cookbook issues, pull requests,
GitHub Project items, migrations to other Theseus repositories, and repository
release/publication work when a release stage is applicable.

GitHub Issues and Projects are coordination and evidence surfaces. They do not
grant permission or acceptance authority.

## Lifecycle states

Use these terms for durable disposition:

```text
ACTIVE / PARKED / MIGRATED / SUPERSEDED / COMPLETED / HISTORICAL / UNKNOWN
```

- **ACTIVE** — current work with a present owner and next acceptance step.
- **PARKED** — intentionally not active; evidence and a safe resume point remain.
- **MIGRATED** — active ownership moved to another canonical issue/repository.
- **SUPERSEDED** — a newer design, branch, issue, or implementation replaces it.
- **COMPLETED** — the declared acceptance criteria and postconditions were met.
- **HISTORICAL** — retained as provenance/evidence, not as current work.
- **UNKNOWN** — current ownership, acceptance, or postcondition is not established.

Project state is a projection of canonical issue/PR disposition, not the source
of authority. A Project item must not be used to infer permission to mutate,
merge, release, or close another object.

## Normal work lifecycle

The shared lifecycle is:

```text
implementation / research slice
  -> local deterministic QA
  -> domain/runtime verification when required
  -> independent review when required
  -> explicit acceptance decision
  -> promotion / merge
  -> release / publication when applicable
  -> exact remote readback
  -> terminal disposition
```

The stages are deliberately separate.

```text
QA PASS != acceptance authority
review approval != merge permission
merge capability != release permission
release completion != scientific acceptance
```

The canonical first local QA gate for this repository is documented in
`tools/dev/README.md`. Network, runtime, provider, GitHub Project, and other
external witnesses remain separate verification layers.

## Migration lifecycle

Migration is used when another repository or issue is the narrower current owner
of active work. migration != acceptance.

Use this order:

```text
target owner
  -> target-side migration receipt
  -> preserve unresolved debt
  -> Project transfer
  -> source disposition
  -> exact remote readback
```

The target-side migration receipt must identify the source issue/PR and preserve
material unresolved review, QA, security, concurrency, portability, or research
debt. Do not close the source first and reconstruct the handoff later.

A migrated source may be closed as not planned/superseded when the work is not
completed in that source. Historical comments and exact branch/commit identities
remain provenance.

## Pull-request disposition

An open PR should have one current role:

- active implementation/review candidate;
- intentionally parked experiment with an explicit resume boundary;
- historical/superseded branch awaiting archival.

Closing an unmerged PR does not mean its implementation was accepted. Record the
exact head SHA and any unresolved review findings before archival when those
facts matter to future work.

Do not merge stale experiments merely to make Project state look clean.

## Issue and Project synchronization

After a canonical issue or PR transition, update the dedicated MarcoPolo
Project so the coordination view does not drift from repository truth.

Examples:

- ACTIVE issue -> Project Status `In Progress`;
- queued active work -> `Todo`;
- COMPLETED / MIGRATED / SUPERSEDED / HISTORICAL source -> `Done`, with the
  terminal meaning recorded in the canonical issue/PR;
- PARKED work may remain open, but its parked state must be explicit in the
  issue and Project maturity/status must not imply current execution.

Project state is a projection; canonical issue/PR evidence wins on conflict.

## Verification and readback

Local deterministic QA proves only the invariants it checks. It does not prove
remote GitHub state.

Important lifecycle mutations require exact remote readback appropriate to the
object:

- issue: state and state reason;
- pull request: state, exact head, and `mergedAt`;
- Project: item identity and relevant field values;
- migration: target-side receipt exists before terminal source disposition;
- release/publication: exact tag/release/artifact identity where applicable.

Executor self-report alone is insufficient when remote readback is available.

## Automation boundary

Automate repetitive checks and already-authorized mechanics, not judgment,
permission, or consequential promotion.

A future roadmap-graph verifier may report deterministic
`PASS / DRIFT / UNAVAILABLE` results, but must remain read-only. Its result may
identify lifecycle drift; it does not authorize closing issues, moving work,
merging PRs, or publishing releases.
