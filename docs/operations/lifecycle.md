# MarcoPolo repository lifecycle v0.1

This is a minimum viable lifecycle policy, not a complete governance framework.
Its purpose is to keep active work, evidence, authority, and terminal disposition
separate with the smallest set of rules justified by observed project failures.

GitHub Issues and Projects are coordination and evidence surfaces. They do not
grant permission or acceptance authority.

## Policy evolution

Evolve this policy in small, reviewable batches. Add a rule only when current
evidence shows a recurring failure class or a concrete uncovered lifecycle gap.
Prefer reversible increments, fast feedback, and the existing QA path over
pre-designing hypothetical future process.

Do not keep a pull request open merely to solve lifecycle cases that have not
been observed. Record a follow-up issue when a real gap appears and iterate.

## Durable states

Use these terms when a durable disposition is needed:

    ACTIVE / PARKED / MIGRATED / SUPERSEDED / COMPLETED / HISTORICAL / UNKNOWN

- ACTIVE: current work with a present owner and next acceptance step.
- PARKED: intentionally inactive, with evidence and a safe resume point.
- MIGRATED: active ownership moved to another canonical issue/repository.
- SUPERSEDED: a newer design, branch, issue, or implementation replaces it.
- COMPLETED: declared acceptance criteria and postconditions were met.
- HISTORICAL: retained as provenance, not current work.
- UNKNOWN: current ownership, acceptance, or postcondition is not established.

Project state is a projection of canonical issue/PR disposition, not authority.

## Normal lifecycle

Use only the stages that are relevant to the artifact:

    implementation / research slice
      -> local deterministic QA
      -> domain/runtime verification when required
      -> independent review when required
      -> explicit acceptance decision
      -> promotion / merge when authorized
      -> release / publication when applicable and authorized
      -> terminal disposition
      -> exact remote readback

The boundaries remain explicit:

    QA PASS != acceptance authority
    review approval != merge permission
    merge capability != release permission
    release completion != scientific acceptance

The canonical first local QA gate is documented in tools/dev/README.md.
External runtime, provider, GitHub, and Project checks remain separate witnesses.

### Independent-review availability states

When an independent Codex review is required, keep provider availability separate
from the review outcome. Use `CODEX_REVIEW_BLOCKED_QUOTA` when the provider
explicitly refuses the review because the code-review usage quota is exhausted.

`CODEX_REVIEW_BLOCKED_QUOTA` means the review did not complete. It is neither a
clean review nor a substantive review failure. Deterministic local QA, issue and
backlog work, design work, and other non-promotional evidence gathering may
continue, but a merge or release gate that explicitly requires Codex exact-head
review remains unsatisfied. Do not silently substitute QA PASS for the missing
review and do not accumulate a long dependent stack of unreviewed implementation
PRs merely to route around the quota. Reprobe when review capability becomes
available, or change the acceptance policy only through an explicit authorized
decision.

## Migration lifecycle

Migration is used when another repository or issue is the narrower current owner
of active work. migration != acceptance.

Use this order:

    target owner
      -> preserve unresolved debt
      -> target-side migration receipt containing that debt
      -> exact target-receipt readback
      -> source disposition
      -> Project synchronization, only when that separate mutation is authorized
      -> exact final readback

Collect material unresolved review, QA, security, concurrency, portability, or
research debt before creating the target-side migration receipt, or atomically
as part of that receipt. Verify the persisted target receipt before disposing
the source. Do not close the source first and reconstruct the handoff later.

Project synchronization follows canonical source disposition; it must not lead
or redefine it. If Project mutation is not authorized or unavailable, leave the
canonical source correct and report Project drift instead of assuming permission.

A migrated source may be closed as not planned/superseded when the work was not
completed there. Historical comments and exact branch/commit identities remain
provenance.

## Pull-request disposition

An open PR should be one of:

- an active implementation/review candidate;
- an intentionally parked experiment with an explicit resume boundary;
- a historical/superseded branch awaiting archival.

Closing an unmerged PR does not mean its implementation was accepted. Preserve
exact head identity and material unresolved review findings before archival when
those facts matter to future work.

Do not merge stale experiments merely to make Project state look clean.

## Verification and readback

Local deterministic QA proves only the invariants it checks. It does not prove
remote GitHub state or lifecycle authority.

Important lifecycle mutations require exact remote readback appropriate to the
object: issue state/reason, PR state/head/mergedAt, Project item fields when the
Project was authorized to change, migration target receipt, and release identity
when release applies.

Executor self-report alone is insufficient when independent readback exists.

## Automation boundary

Automate repetitive checks and already-authorized mechanics, not judgment,
permission, or consequential promotion.

A roadmap verifier may report PASS / DRIFT / UNAVAILABLE, but remains read-only.
Its result can identify lifecycle drift; it cannot authorize closing issues,
moving work, merging PRs, or publishing releases.
