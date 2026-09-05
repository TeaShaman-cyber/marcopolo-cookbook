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

The first implementation contract should be deliberately small:

```text
memory_recall(query, scope) -> evidence_packet
memory_retain(event) -> receipt
memory_readback(event_id) -> stored_event
memory_reconcile(scope) -> conflicts / duplicates / status
```

Minimum requirements:

- deterministic structured input/output;
- explicit provenance/source class;
- exact readback after writes;
- idempotent logical-event handling;
- duplicate and conflict visibility;
- `search miss = UNKNOWN`, never automatic absence;
- no retained observation silently becomes canonical cookbook authority.

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

### 1. Append-only JSONL receipts

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

### 2. Minimal SQLite + FTS5

Purpose: small searchable operational memory.

Candidate shape:

```text
append/event table
current fact/materialization table
FTS5 search
lifecycle/conflict metadata
```

No embedding requirement.

### 3. Hermes Holographic-style backend

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

### 4. DuckDB

Purpose: deterministic structured reference backend and strong analytical read model.

Useful for:

- exact scoped filtering;
- provenance/currentness queries;
- conflict analysis;
- rebuilding compact evidence packets.

Historical warning: a real MarcoPolo DuckDB transient writer lock was observed when a second Python process held the DB. This proves writer contention occurred; it does **not** prove NFS was the root cause.

### 5. External/service-backed provider

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

## Canonical-evidence option

A preferred safety shape to test is:

```text
append-only receipts        <- canonical evidence
        ↓
rebuildable projection      <- disposable/searchable state
    ↙           ↘
SQLite/Holo     DuckDB
```

If a mutable index becomes corrupted or locking behavior proves unsafe, the projection can be rebuilt without losing the canonical event history.

## Falsifiable experiment

### Probe A — storage identity

Determine the actual current persistent-filesystem characteristics relevant to locking/durability. Record facts; do not infer from path names alone.

### Probe B — JSONL durability control

Write one synthetic event, exact-read it, reopen from a fresh process/session, then exercise interrupted and concurrent writes.

### Probe C — deterministic DB backend

Run the same corpus and lifecycle against DuckDB and/or minimal SQLite/FTS5. Compare lock behavior, recovery, and readback.

### Probe D — recall

Seed one synthetic operational observation. In a fresh relevant task, the Skill-directed route should recall it without the user naming the row.

### Probe E — retain

Run a harmless task producing one new verified synthetic lesson. Require one structured retain transaction plus exact readback.

### Probe F — fresh-session reuse

Start a fresh client chat and issue a materially similar task. The retained event should be recalled and influence route selection.

### Probe G — negative control

An unrelated task should neither recall the event nor create a new memory row.

### Probe H — duplicate/conflict

Repeated observations must not amplify uncontrolled duplicates. Contradictory applicable observations must surface conflict/`UNKNOWN`, not silently choose one.

### Probe I — interruption

Interrupt after meaningful work but before model-mediated retain. Missing persistence must remain visibly missing. This distinguishes best-effort Skill-directed retention from a host-enforced post-turn callback.

### Probe J — Holographic comparison

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