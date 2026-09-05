# Memory provider roadmap — shared PostgreSQL substrate hypotheses

Status: `ROADMAP / HYPOTHESES — NOT IMPLEMENTATION`
Tracks: #17 / PR #20

This roadmap records follow-up ideas discovered after the managed-PostgreSQL core probe. It does not change the current adapter contract, enable database extensions, or promote any hypothesis into accepted architecture.

## Working direction

Treat durable storage and retrieval semantics as separate layers:

```text
managed PostgreSQL
    ├── durable event / fact state
    ├── lexical retrieval projection
    ├── entity / relation / trust projection
    └── optional vector projection
```

The database may be shared while the authority classes remain separate.

Do **not** collapse forensic session evidence, operational semantic memory, and derived vector/search indexes into one authority class merely because they share PostgreSQL.

## R0 — Remote PostgreSQL as authoritative mutable substrate

Current synthetic evidence in PR #20 establishes a viable remote PostgreSQL write/read/idempotency path through MarcoPolo. Continue treating this as a candidate authoritative mutable store while local `/workspace` databases remain comparison, cache, or rebuildable projection lanes unless separately proven safe.

## R1 — Hindsight lineage: embeddings can live beside durable memory in PostgreSQL

Current Hindsight architecture uses PostgreSQL 14+ plus a vector extension for similarity search. `pgvector` is the default, with other PostgreSQL vector extensions supported. Production documentation explicitly supports external PostgreSQL providers including Neon and Supabase.

Roadmap hypothesis:

```text
facts / observations / lifecycle state
            +
embedding vectors
            ↓
        PostgreSQL
```

This is evidence that a separate vector database is not structurally required for a useful semantic-memory system.

Do not adopt Hindsight's full runtime or extraction pipeline by implication. The reusable idea here is narrower: PostgreSQL can hold both ordinary durable state and vector projections.

References:
- https://github.com/vectorize-io/hindsight
- https://github.com/vectorize-io/hindsight/blob/main/skills/hindsight-docs/references/developer/installation.md
- https://github.com/vectorize-io/hindsight/blob/main/skills/hindsight-docs/references/developer/configuration.md

## R2 — Holographic semantics should be separable from SQLite storage

Current Hermes Holographic combines:

```text
SQLite + FTS5
trust scoring
entity resolution
probe / related / reason / contradict
optional HRR algebra
```

The roadmap question is not "replace Holographic with Postgres". It is:

> Can the useful Holographic fact/entity/trust/reasoning semantics survive behind the same backend-neutral adapter when the storage substrate is PostgreSQL rather than SQLite?

Candidate decomposition:

```text
Holographic semantics
    ├── fact lifecycle
    ├── entity links
    ├── trust / feedback
    ├── contradiction relations
    └── HRR / compositional representation
            ↓
storage adapter
            ↓
PostgreSQL
```

Possible PostgreSQL projections:

```text
facts / entities / relations     -> ordinary relational tables
lexical search                   -> PostgreSQL FTS or optional pg_search
vector-like semantic projection  -> optional pgvector where appropriate
HRR state                        -> separate explicit representation; do not silently equate HRR with embeddings
```

Preserve the distinction between HRR compositional representations and ordinary embedding vectors. Sharing a vector-capable database does not make those representations semantically identical.

Reference:
- https://github.com/NousResearch/hermes-agent/tree/main/plugins/memory/holographic

## R3 — Session Search lineage: SQLite + FTS is already a known projection pattern

The original Theseus Session Search explicitly treats raw accepted artifacts as durable evidence and SQLite/FTS as a **regeneratable projection**:

```text
accepted raw session artifacts / ledger
            ↓
regeneratable SQLite + FTS projection
            ↓
forensic lexical search
```

Holographic's current `SQLite + FTS5` substrate therefore belongs to the same broad storage/index family, but its role is different:

```text
Session Search
  purpose   = forensic retrieval of what was actually said
  authority = raw accepted artifacts
  SQLite    = disposable search projection

Holographic
  purpose   = operational fact memory + entity/trust/reasoning semantics
  authority = currently the fact store itself
  SQLite    = durable local store + search substrate
```

Roadmap consequence: before building a new lexical subsystem, inspect whether Session Search already contains reusable ingestion, FTS, provenance, deterministic rebuild, scope, and evidence-packet patterns. Avoid independently rebuilding the same SQLite/FTS machinery under a new name.

Longer-term hypothesis:

```text
raw session evidence ───────────┐
                               │
operational fact memory ────────┼──> shared PostgreSQL substrate
                               │        ├── lexical projections
entity/trust relations ─────────┤        ├── exact/filter lanes
                               │        └── optional vectors
embedding projections ──────────┘
```

The shared physical database must **not** erase the logical authority boundary between raw evidence and derived semantic memory.

Local references:
- `/workspace/tools/session-search/README.md`
- `/workspace/theseus-session-search-lab/README.md`

## R4 — PostgreSQL lexical retrieval lane

Do not assume SQLite FTS5 must be replicated literally in PostgreSQL.

Compare at least:

1. built-in PostgreSQL full-text search (`tsvector` / GIN);
2. optional `pg_search` if operationally justified;
3. external lexical/search projection only if PostgreSQL-native options are measurably insufficient.

The current disposable Neon probe reports these extensions as **available but not installed**:

```text
vector    0.8.0
pg_search 0.15.26
```

Extension installation is a separate future mutation and requires its own acceptance decision. Availability is not adoption.

## R5 — Optional vector lane

Only add embeddings after deterministic exact/filter and lexical recall have a measured semantic-recall limitation.

If vector retrieval is justified:

```text
canonical text / fact
      ↓ deterministic embedding function
vector projection in PostgreSQL
      ↓
semantic candidate retrieval
      ↓
normal provenance / conflict / lifecycle checks
```

The vector is a projection, not authority. Re-embedding should be possible from retained canonical text without rerunning unrelated extraction or changing the durable event identity.

Questions for a later spike:

- Which embedding model/dimension is small enough for the free tier and current workload?
- Can vectors be regenerated deterministically from canonical retained text?
- How are embedding-model/version migrations represented without rewriting historical authority?
- How is semantic ranking combined with conflict-complete recall rather than allowed to hide contradictions?

## R6 — One database, multiple logical schemas

A possible target shape, not yet a decision:

```text
PostgreSQL
  evidence.*     raw artifact references / immutable evidence metadata
  memory.*       accepted operational observations / facts / lifecycle state
  relations.*    entities / links / trust / contradiction metadata
  search.*       rebuildable lexical materializations
  vector.*       rebuildable embedding projections
```

This is attractive because transaction, concurrency, backup, and access-control primitives are shared while logical authority remains explicit.

Alternative: separate databases/schemas if isolation or quotas prove more important than shared transactions. Measure before choosing.

## Guardrails

- `shared PostgreSQL` does not mean `shared authority`.
- Raw session evidence must remain distinguishable from semantic facts and derived projections.
- FTS/vector indexes are rebuildable projections unless explicitly promoted by a separate authority decision.
- Holographic semantics must be tested independently from its current SQLite implementation.
- HRR and embeddings are different representation families even if both can be stored in vector-shaped columns.
- No database extension is enabled merely because the provider offers it.
- No embedding lane is introduced before lexical/exact retrieval has a measured limitation.
- Backend-neutral core conformance remains a prerequisite for comparing PostgreSQL, SQLite/Holographic, Session Search projections, or any future provider.

## Suggested future order

```text
1. finish backend-neutral core contract
2. adapter-only recall/retain probe on PostgreSQL
3. compare Session Search lexical semantics with PostgreSQL FTS
4. prototype Holographic storage adapter on PostgreSQL while preserving semantics
5. only then test optional pgvector embedding projection
6. compare usefulness / cost / latency against simpler lexical + structured recall
```

The intended direction is convergence of **storage primitives**, not premature convergence of memory meanings.

---

Prepared collaboratively by Semyon Poklad and Шут (Jester), ChatGPT / GPT-5.6 Sol.
