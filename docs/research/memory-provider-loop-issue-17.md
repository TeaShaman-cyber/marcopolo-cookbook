# MarcoPolo Skill-directed memory loop — research contract

Status: `RESEARCH / DESIGN REVIEW`
Tracks: #17

## Feynman version

The hypothesis is simple:

```text
Skill tells the agent when to remember
        ↓
small adapter recalls relevant memory
        ↓
agent works normally through MarcoPolo
        ↓
verified reusable delta appears
        ↓
same adapter retains it
        ↓
next session can recall it
```

The experiment is about the **loop**, not DuckDB, SQLite, Holographic, or any other one database.

## Research question

Can the existing MarcoPolo `Skill -> model -> MCP/workspace` path support a useful model-mediated memory lifecycle with a pluggable backend:

```text
recall -> work -> retain -> readback -> later recall
```

without requiring, for the first useful version:

- a separate memory LLM;
- embeddings;
- a vector database;
- a background daemon;
- automatic cookbook mutation;
- an unverified host lifecycle hook.

A successful result may be called a **Skill-directed recall/retain loop** or **model-mediated operational memory loop**.

It must not be called a host-level `MemoryProvider` until deterministic lifecycle callbacks are independently observed.

## Why the Skill matters

The current MarcoPolo Skill is already a thin recall/router contract: classify the operation, load only the smallest relevant cookbook guidance, use the thinnest valid route, verify the postcondition, and preserve reusable operational lessons without turning the Skill itself into a knowledge base.

The proposed extension is symmetric:

```text
persistent state -> bounded recall -> model
model -> verified delta -> persistent state
```

The Skill remains the policy/routing layer. The memory backend remains replaceable.

## Backend-neutral adapter

The first implementation contract should be deliberately small, but its retry and recall semantics must be normative:

```text
memory_recall(query, scope) -> evidence_packet
memory_retain(operation_id, event) -> receipt
memory_readback(event_id) -> stored_event
memory_reconcile(scope) -> conflicts / duplicates / status
```

`operation_id` is caller-stable across retries of the same logical retain attempt. Before the first write, the admission-approved request is serialized into canonical UTF-8 JSON (sorted object keys, no insignificant whitespace) and hashed as:

```text
request_fingerprint = sha256(canonical_request_bytes)
```

The canonical row binds `operation_id` to that fingerprint. A successful retain creates and stores one **immutable receipt** only after the canonical accepted bytes have crossed the backend's documented durable commit point:

```text
receipt_version
operation_id
request_fingerprint
event_id
committed_at
commit_state = DURABLY_COMMITTED
```

`inserted=true/false`, retry count, transport timing, and similar values are **attempt-local diagnostic** metadata; they are not fields of the immutable logical receipt.

```text
DURABLY_COMMITTED
  = canonical accepted bytes + immutable receipt committed before success acknowledgement

lost acknowledgement after commit
  -> retry the same operation_id with the same canonical bytes
  -> recompute the same request_fingerprint
  -> resolve the already committed logical event
  -> return the same stored receipt
  -> attempt-local diagnostic may report inserted=false
  -> never create a second observation merely because the acknowledgement was lost
```

If the same `operation_id` arrives with a different `request_fingerprint`, the backend must fail closed with `IDEMPOTENCY_KEY_REUSE_MISMATCH`. In other words, **same operation_id with different canonical bytes** is an error, not a retry and not a successful replay. No new event is written and the old event must not be presented as acceptance of the new payload.

Backends must expose lookup by `operation_id` and compare the stored request fingerprint before replaying a receipt. Projection/index update may lag the canonical commit, but readback of the committed logical event must not silently manufacture a second event.

Recall is **conflict-complete recall**, not merely top-N matching. One logical recall operation must derive its matches and applicability state from the same snapshot or an equivalent atomic view:

```text
memory_recall(query, scope)
  -> matches
  + applicable conflicts
  + supersession state
  + tombstone state
```

A matching observation must not be returned as uncontested if an applicable contradiction, superseding record, or tombstone exists outside the ordinary retrieval cutoff. `memory_reconcile()` may remain a maintenance operation, but conflict visibility required for a decision cannot depend on a later optional call.

### Core conformance lane

Every backend must implement one versioned deterministic portable lane before richer retrieval is compared. **stable IDs** are normative across all backends and survive projection rebuilds:

```text
core_schema_version = memory-core-v0.1
```

Normative lifecycle vocabulary:

```text
OBSERVED | CANDIDATE | PENDING | SUPERSEDED | TOMBSTONED
```

Authorization precedes portable recall semantics. The model/request may name a requested `scope`, but that string is **not** an authorization credential. The adapter receives a `trusted_execution_context` from the harness/wrapper boundary; it must contain or resolve a `trusted_principal_id` that the model cannot forge. Policy maps that principal to `allowed_scopes`.

```text
trusted_execution_context
  -> trusted_principal_id
  -> policy lookup
  -> allowed_scopes
  -> validate requested scope
  -> effective_scope
  -> backend query/write only after authorization
```

If the requested scope is not allowed, return `AUTHZ_SCOPE_DENIED` **before any backend query** or durable write. A missing/untrusted principal fails closed. Backend adapters receive only an authorized `effective_scope`; they must not infer authority from caller-controlled text. The shared fixture defines `memory-authz-v0.1` principals and both allowed and denied cases.

Normative exact/filter recall request for `memory-core-v0.1` after authorization:

```text
scope                  required exact requested scope; validated into effective_scope
filters.event_id       optional exact string
filters.operation_id   optional exact string
filters.source_class   optional exact string
filters.lifecycle      optional set from the normative vocabulary
filters.created_after  optional inclusive RFC3339 timestamp
filters.created_before optional exclusive RFC3339 timestamp
limit                  integer 1..100, default 20
cursor                 optional opaque continuation token
```

Core matching is exact/filter-only. Apply scope and filters first, then use the normative deterministic ordering:

```text
created_at DESC, event_id ASC
```

Pagination is keyset pagination. The portable cursor representation is:

```text
cursor = base64url(created_at, event_id)
```

For `memory-core-v0.1`, that notation means base64url without `=` padding over UTF-8 bytes of `created_at + "\n" + event_id`, with `created_at` serialized as canonical UTC RFC3339 `YYYY-MM-DDTHH:MM:SSZ` in the conformance fixture.

The cursor resumes strictly after the last emitted `(created_at, event_id)` under the normative ordering. `limit` changes page size only; it must not change match semantics. Ranked FTS, vector similarity, Holographic reasoning, or provider-specific scores cannot influence this core ordering.

The normalized `evidence_packet` contains:

```text
core_schema_version
scope = authorized effective_scope
items[]
conflicts[]
supersession[]
tombstones[]
next_cursor | null
result_state = HIT | MISS_UNKNOWN | CONFLICT
```

Each item must expose stable `event_id`, `operation_id` when present, `source_class`, `lifecycle_state`, `created_at`, explicit provenance, and canonical payload reference/content according to the fixture. Relationship entries also carry stable relation IDs, explicit `relation.scope`, and provenance. Conflict, supersession, and tombstone state must come from the **same decision snapshot** as the items and are not clipped merely because the related event falls outside the page `limit`. In particular, a returned item with an applicable contradiction outside the normal page cutoff must surface that relation in `conflicts[]`.

Relationship safety is scoped before persistence and before recall. For every conflict, supersession, or tombstone relation:

```text
relation.scope == endpoint_1.scope == endpoint_2.scope == effective_scope
```

The retention/admission boundary must resolve endpoint events inside the authorized `effective_scope` and reject any relation whose endpoint scope differs with `RELATION_SCOPE_MISMATCH` **before canonical durable write**. Normal relationship sidecar lookup is constrained to `relation.scope = effective_scope`; cross-scope relations are not an alternate channel for discovering another scope.

Before returning any normal recall packet, the backend must also run an **authorized endpoint integrity probe** using only the already-authorized page `event_id` values. This probe is **independent of relation.scope**: it inspects every stored relationship that references an authorized endpoint, regardless of the relationship's claimed scope label, and verifies:

```text
relation.scope == each endpoint event.scope == effective_scope
```

This is an internal integrity check, not a retrieval surface. If the probe detects a wrong relation scope, cross-scope endpoint, missing endpoint, or equivalent invariant violation, it returns only the **generic INTEGRITY_SCOPE_VIOLATION** failure. It **must not expose relation IDs**, unauthorized endpoint IDs, relation provenance, or unauthorized payload metadata. Only after this endpoint-driven integrity check passes may normal same-scope relationship sidecars be assembled.

If a legacy/corrupt row violates this invariant and is encountered during recall or reconciliation, return `INTEGRITY_SCOPE_VIOLATION` instead of a normal evidence packet. That failure **must not expose unauthorized endpoint IDs** or their provenance/payload metadata. Conflict completeness therefore means complete applicable safety state **within the authorized effective scope**, never cross-scope disclosure. The conformance fixture includes fail-closed conflict, supersession, and tombstone vectors for both endpoint-scope mismatch and wrong `relation.scope` labels.

A zero-item exact/filter result returns `MISS_UNKNOWN`, not proof of absence.

A backend passes **fixture-exact conformance** only when the shared fixture corpus and request vectors in `tests/fixtures/memory-core-v0.1.json` produce the same full normalized packet, including provenance, safety-state relationships, ordering, lifecycle interpretation, `MISS_UNKNOWN`, and pagination boundaries. The executable fixture test is `tests/test_memory_core_fixture.py`. Backend-specific diagnostics may be emitted separately but are excluded from the normalized packet.

Ranked FTS, Holographic `probe` / `related` / `reason`, semantic similarity, and other richer retrieval are optional capabilities above the Core conformance lane. Backend replacement is not considered meaningful if the deterministic lane changes its semantics.

Minimum requirements therefore include:

- deterministic structured input/output;
- explicit provenance/source class;
- exact readback after writes;
- caller-stable idempotent logical-event handling;
- duplicate and conflict visibility from the decision snapshot;
- `search miss = UNKNOWN`, never automatic absence;
- no retained observation silently becomes canonical cookbook authority.

## Retention safety boundary

The model may propose a candidate event, but it is not the admission authority. A **retention admission gate** outside the model must run before canonical durable write:

```text
model proposal
  -> schema validation
  -> scope isolation
  -> size limit
  -> content / adversarial-input checks
  -> secret / credential rejection
  -> ACCEPT or REJECT
  -> canonical durable write only after ACCEPT
```

In other words, secret or credential material must be rejected **before canonical durable write**. A later tombstone can invalidate ordinary semantic content, but it is not an acceptable erasure mechanism for a secret that was already durably appended.

The acceptance suite must include a synthetic **secret canary**, adversarial content, and a cross-scope event. Cross-scope denial is evaluated against the trusted principal policy, not against model-provided labels. Expected behavior is `AUTHZ_SCOPE_DENIED` before persistence/query and no recall from an unauthorized scope.

## Authority boundary

Keep two layers separate:

```text
operational memory backend
  = observations, receipts, candidates, conflicts, applicability

accepted cookbook
  = reviewed reusable operational guidance
```

Automatic retain may record:

```text
OBSERVED:
workspace route X failed before target execution with failure class Y
```

It must not silently promote:

```text
RULE:
always use route Z for every future operation of this class
```

Derived rules remain `CANDIDATE` / `PENDING` until separately accepted.

## Candidate backends

### 1. Managed PostgreSQL — first-class remote lane

Managed PostgreSQL is an **authoritative mutable store candidate** for the first production-shaped storage probe:

```text
Skill / model
    -> memory adapter
    -> MarcoPolo governed pg connection
    -> managed PostgreSQL
```

This lane deliberately moves mutable concurrency and durability away from the MarcoPolo local filesystem. Candidate primitives map cleanly to the contract:

- `operation_id UNIQUE` plus stored `request_fingerprint` comparison gives a deterministic idempotency primitive; `ON CONFLICT` alone is insufficient;
- transaction commit is the candidate `DURABLY_COMMITTED` point;
- conflict-complete recall can read matches, conflicts, supersession, and tombstones from one transaction snapshot;
- database credentials remain outside `/workspace` behind the MarcoPolo connection boundary.

For this experiment, **Neon is the first free-tier probe target, not an architectural dependency on Neon**. Supabase, Prisma Postgres, or another compatible managed PostgreSQL provider may implement the same lane later.

The **local embedded backends** below remain comparison / cache / rebuildable projection candidates unless a later experiment promotes one with explicit filesystem and concurrency evidence.

### 2. Append-only JSONL receipts

Purpose: lowest-complexity durability control.

```text
immutable event receipts
        ↓
rebuildable projection
```

Strengths:

- transparent bytes;
- easy hash/readback;
- no database engine required for canonical evidence;
- useful recovery source when projections are disposable.

Risks to test:

- concurrent append semantics on current MarcoPolo storage;
- process interruption during write;
- atomicity and durable flush behavior.

### 3. Minimal SQLite + FTS5

Purpose: small searchable operational memory.

Candidate shape:

```text
append/event table
current fact/materialization table
FTS5 search
lifecycle/conflict metadata
```

No embedding requirement.

### 4. Hermes Holographic-style backend

Current upstream Hermes Holographic is an attractive reference because its core is lightweight:

```text
SQLite + FTS5
trust scoring
entity resolution
probe / related / reason / contradict
optional NumPy HRR
```

The experiment may either adapt its implementation or reproduce only the useful storage/retrieval semantics behind the MarcoPolo adapter.

Do not assume the SQLite file is safe on MarcoPolo persistent storage until the storage gate below passes.

### 5. DuckDB

Purpose: deterministic structured reference backend and strong analytical read model.

Useful for:

- exact scoped filtering;
- provenance/currentness queries;
- conflict analysis;
- rebuilding compact evidence packets.

Historical warning: a real MarcoPolo DuckDB transient writer lock was observed when a second Python process held the DB. This proves writer contention occurred; it does **not** prove NFS was the root cause.

### 6. External/service-backed provider

Hindsight, OpenViking, or another service-backed provider is a comparison lane if embedded-file durability on MarcoPolo proves unsafe or operationally brittle.

This lane is intentionally later because it adds service/auth/dependency cost.

### MemPalace

Historical Theseus MemPalace remains a useful design lineage for graph/spatial/re-entrant navigation ideas, but no current persistent backend is assumed verified. Recover useful semantics only after identifying a concrete current implementation and acceptance route.

## Storage/NFS acceptance gate

Backend capability and filesystem safety are separate facts.

For every embedded-file backend, test on the **actual current MarcoPolo persistence surface**:

```text
FILESYSTEM_IDENTITY
single writer
concurrent reader
second concurrent writer
process crash during write
restart / reopen
journal or WAL recovery where applicable
atomic rename / append behavior
fresh-session readback
integrity / corruption check
```

Classify independently:

```text
ENGINE_OK
FILESYSTEM_OK
CONCURRENCY_OK
CRASH_RECOVERY_OK
PERSISTENCE_OK
```

`import sqlite3`, `import duckdb`, or one successful write is not acceptance.

Do not attribute an observed lock to NFS unless filesystem-specific evidence supports that causal claim.

## Canonical-evidence options

Two different safety shapes should be compared rather than collapsed:

```text
remote authoritative lane
managed PostgreSQL <- canonical mutable state
        ↓
optional local cache / analytical projection

local evidence lane
append-only receipts <- canonical evidence
        ↓
rebuildable projection
    ↙           ↘
SQLite/Holo     DuckDB
```

The managed-Postgres probe asks whether the remote lane removes local-file locking from the authoritative write path. The local receipt shape remains valuable as a transparent comparison/recovery lane. If a local mutable index becomes corrupted, it should remain rebuildable rather than becoming the sole copy of accepted state.

## Falsifiable experiment

### Probe A — managed PostgreSQL transport and write semantics

Using a synthetic free-tier PostgreSQL target, prove the smallest remote path independently of the memory loop:

```text
MarcoPolo pg sentinel
-> synthetic table create
-> insert with caller-stable operation_id
-> exact readback
-> retry same operation_id with identical canonical bytes -> same stored receipt
-> reuse same operation_id with different canonical bytes -> IDEMPOTENCY_KEY_REUSE_MISMATCH
-> exactly one logical row
-> fresh independent MarcoPolo invocation readback
```

A PASS here proves only the tested governed transport and storage postconditions. It does not prove Skill auto-selection, adapter attribution, cross-worker persistence, or host-level MemoryProvider lifecycle behavior.

### Probe B — local storage identity

Determine the actual current persistent-filesystem characteristics relevant to locking/durability for local embedded backends. Record facts; do not infer from path names alone.

### Probe C — JSONL durability control

Write one synthetic event, exact-read it, reopen from a fresh process/session, then exercise interrupted and concurrent writes.

### Probe D — deterministic local DB backend

Run the same corpus and lifecycle against DuckDB and/or minimal SQLite/FTS5. Compare lock behavior, recovery, and readback.

### Probe E — recall and adapter attribution

Seed one synthetic **adapter-only canary** that exists only in the selected backend and is absent from the Skill, current chat, project fixtures, and other test memory surfaces. Instrument the adapter invocation.

Run three controls:

```text
direct adapter read -> expected HIT
Skill-directed task with adapter enabled -> expected HIT plus adapter-call receipt
materially identical task with adapter disabled -> expected MISS / UNKNOWN
```

A successful model answer without an observable adapter call does not establish adapter attribution. A failed Skill-directed call must also be separated from direct-adapter backend failure.

### Probe F — retain

Run a harmless task producing one new verified synthetic lesson. Require one structured retain transaction plus exact readback.

### Probe G — fresh-session reuse

Start a fresh client chat and issue a materially similar task. The retained event should be recalled and influence route selection.

### Probe H — negative control

An unrelated task should neither recall the event nor create a new memory row.

### Probe I — duplicate/conflict

Repeated observations must not amplify uncontrolled duplicates. Contradictory applicable observations must surface conflict/`UNKNOWN`, not silently choose one.

Place an applicable contradiction deliberately outside the normal top-N retrieval cutoff. The decision packet must still surface the conflict from the same snapshot rather than returning the top match as uncontested.

### Probe J — interruption, acknowledgement loss, and client boundary

Interrupt after meaningful work but before model-mediated retain. Missing persistence must remain visibly missing. This distinguishes best-effort Skill-directed retention from a host-enforced post-turn callback.

Separately inject or simulate the boundary:

```text
canonical append / commit succeeds with stored immutable receipt
-> success acknowledgement is lost
-> caller retries the same operation_id and identical canonical bytes
-> same stored receipt is replayed
-> exactly one logical event remains

same operation_id + different canonical bytes
-> request_fingerprint mismatch
-> IDEMPOTENCY_KEY_REUSE_MISMATCH
-> no new event is written
```

Where the runtime exposes genuinely distinct storage clients, workers, mounts, or executor replacement, repeat readback and contention across that boundary. If the current MarcoPolo surface cannot positively establish such a boundary, preserve the result explicitly as:

```text
CROSS_CLIENT_PERSISTENCE = UNKNOWN
```

A same-process or same-mount reopen must not be promoted into a stronger cross-client claim.

### Probe K — Holographic comparison

Only after SQLite/storage placement passes, run the same synthetic corpus through Holographic-style search/probe/related/contradiction semantics and compare retrieval usefulness against the deterministic baseline.

## First-pass metrics

```text
recall_trigger_precision
relevant_memory_precision
false_recall_rate
retain_attempt_rate
retain_readback_rate
duplicate_amplification_rate
conflict_hidden_rate
write_without_readback_rate
storage_lock_failure_rate
crash_recovery_failure_rate
```

Hard safety targets:

```text
conflict_hidden_rate        = 0
write_without_readback_rate = 0
search_miss_to_absence_rate = 0
unsafe_active_retain_rate   = 0
```

## Non-goals

- claiming equivalence to Hindsight or Hermes host lifecycle hooks;
- building a new always-on memory service before the loop is proven;
- introducing embeddings before deterministic retrieval has a measured limitation;
- automatically rewriting the accepted cookbook;
- treating `/workspace` persistence semantics as known without a fresh probe;
- turning every completed task into retained memory.

## Decision gate

Proceed to implementation only if design review finds no blocking conceptual error and the smallest storage probe can distinguish:

```text
loop failure
vs
backend failure
vs
filesystem/locking failure
vs
Skill-routing failure
```

The first implementation should remain small enough that replacing the backend does not require rewriting the Skill.

---

Prepared collaboratively by Semyon Poklad and Шут (Jester), ChatGPT / GPT-5.6 Sol.