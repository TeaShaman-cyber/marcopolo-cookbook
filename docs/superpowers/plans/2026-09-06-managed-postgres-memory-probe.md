# Managed Postgres Memory Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the pluggable memory-loop research contract, make managed PostgreSQL a first-class backend lane, and run one synthetic Neon-through-MarcoPolo write/readback/idempotency probe without implementing a production memory provider.

**Architecture:** The Skill-directed lifecycle stays backend-neutral. Managed PostgreSQL becomes an authoritative mutable-store candidate reached only through MarcoPolo's governed `pg` connection; JSONL, SQLite/Holographic and DuckDB remain comparison/cache/projection lanes. The live probe proves only transport, remote mutation, readback and retry semantics.

**Tech Stack:** Markdown, Python unittest, MarcoPolo `connection` CLI, PostgreSQL, Neon free tier, governed `gh-write`, read-only GitHub verification.

**Spec:** `docs/research/memory-provider-loop-issue-17.md`

## Global Constraints

- Skill guidance is model-mediated, not a proven host lifecycle callback.
- Backend contract stays replaceable; Neon is a probe target, not an architectural dependency.
- No embeddings, helper LLM, vector DB, daemon, or automatic cookbook mutation.
- `search miss = UNKNOWN`; `unsafe_active_retain_rate = 0`; `conflict_hidden_rate = 0`; `write_without_readback_rate = 0`.
- Secret/credential material must be rejected before canonical durable write.
- GitHub writes go only through MarcoPolo `gh-write`; GitHub connector is read-only verification.
- Live DB probes use synthetic canaries and publish no connection strings, passwords, tokens, or provider credentials.

---

### Task 1: Harden the contract against Codex findings

**Files:**
- Modify: `docs/research/memory-provider-loop-issue-17.md`
- Create: `tests/test_memory_provider_loop_contract.py`

**Interfaces:**
- Consumes: current PR #20 contract and six Codex findings.
- Produces: caller-stable retain IDs, durable commit semantics, conflict-complete recall, external admission gate, adapter attribution controls, portable core conformance, and bounded cross-client claims.

- [ ] **Step 1: Write failing contract tests**

Create a unittest that loads the research document and requires these exact markers:

```python
from pathlib import Path
import unittest

DOC = Path(__file__).resolve().parents[1] / 'docs/research/memory-provider-loop-issue-17.md'

class MemoryProviderLoopContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOC.read_text(encoding='utf-8')

    def test_retain_commit(self):
        for marker in ('operation_id', 'DURABLY_COMMITTED', 'lost acknowledgement'):
            self.assertIn(marker, self.text)

    def test_conflict_complete_recall(self):
        for marker in ('conflict-complete recall', 'same snapshot', 'tombstone'):
            self.assertIn(marker, self.text)

    def test_admission_precedes_write(self):
        for marker in ('retention admission gate', 'before canonical durable write', 'secret canary'):
            self.assertIn(marker, self.text)

    def test_adapter_attribution(self):
        for marker in ('adapter-only canary', 'adapter disabled', 'direct adapter'):
            self.assertIn(marker, self.text)

    def test_core_conformance(self):
        for marker in ('Core conformance lane', 'stable IDs', 'deterministic ordering'):
            self.assertIn(marker, self.text)

    def test_cross_client_unknown(self):
        self.assertIn('CROSS_CLIENT_PERSISTENCE', self.text)
        self.assertIn('UNKNOWN', self.text)
```

- [ ] **Step 2: Run RED**

```bash
python3 -m unittest tests/test_memory_provider_loop_contract.py
```

Expected: FAIL on missing normative markers.

- [ ] **Step 3: Update the research contract**

Normative retain contract:

```text
memory_retain(operation_id, event) -> receipt
operation_id = caller-stable across retries
DURABLY_COMMITTED = canonical accepted bytes committed before success receipt
lost acknowledgement + retry same operation_id -> return existing logical event/receipt
```

Normative recall packet:

```text
memory_recall(query, scope)
  -> matches
  + applicable conflicts
  + supersession state
  + tombstones
```

Require a **retention admission gate** outside the model before canonical durable write: schema, scope, size, secret/content checks -> ACCEPT/REJECT -> only ACCEPT may persist.

Define a **Core conformance lane** for every backend: stable IDs, scope, lifecycle/source state, provenance, exact deterministic filters, deterministic ordering, pagination/cutoff, and conflict/supersession/tombstone semantics. Ranked/Holographic behavior is optional capability above it.

Add falsification probes for: lost acknowledgement retry, contradiction outside normal top-N, adapter-only canary with direct-adapter and adapter-disabled controls, secret/adversarial/cross-scope retain, and distinct client/executor replacement when observable. If not observable, classify `CROSS_CLIENT_PERSISTENCE = UNKNOWN`.

- [ ] **Step 4: Verify**

```bash
python3 -m unittest tests/test_memory_provider_loop_contract.py
python3 -m unittest tests/test_candidate_skill_contract.py
bash tests/python-bootstrap.sh
bash tests/wiki-push.sh
git diff --check
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/research/memory-provider-loop-issue-17.md tests/test_memory_provider_loop_contract.py
git commit -m 'docs: harden memory loop research contract'
```

---

### Task 2: Add managed PostgreSQL as a first-class backend lane

**Files:**
- Modify: `docs/research/memory-provider-loop-issue-17.md`
- Modify: `tests/test_memory_provider_loop_contract.py`

**Interfaces:**
- Consumes: Task 1 backend-neutral contract.
- Produces: explicit remote managed-Postgres candidate without binding architecture to Neon.

- [ ] **Step 1: Add RED assertions** requiring `Managed PostgreSQL`, `authoritative mutable store candidate`, `local embedded backends`, and `not an architectural dependency on Neon`.
- [ ] **Step 2: Run focused unittest and verify RED.**
- [ ] **Step 3: Document topology:**

```text
Skill/model -> memory adapter -> MarcoPolo governed pg connection -> managed PostgreSQL

Managed PostgreSQL = authoritative mutable store candidate
local embedded backends = comparison / cache / rebuildable projection candidates
```

Record: transaction commit as candidate durable commit point; `operation_id UNIQUE` / `ON CONFLICT` as idempotency primitives; one transaction snapshot for conflict-complete recall; credentials remain outside `/workspace`. State exactly: `Neon is the first free-tier probe target, not an architectural dependency on Neon.`

- [ ] **Step 4: Run Task 1 verification set; expect all PASS.**
- [ ] **Step 5: Commit:**

```bash
git add docs/research/memory-provider-loop-issue-17.md tests/test_memory_provider_loop_contract.py
git commit -m 'docs: add managed postgres memory backend lane'
```

---

### Task 3: Run a synthetic Neon-through-MarcoPolo pg probe

**Files:**
- Create after probe: `artifacts/issue-17/managed-postgres-probe-20260906.json`
- Create after probe: `artifacts/issue-17/managed-postgres-probe-20260906.md`

**Interfaces:**
- Consumes: disposable Neon project and MarcoPolo `pg` connection.
- Produces: non-secret receipt for sentinel, remote write, exact readback, idempotent retry, fresh invocation persistence, and explicit cross-client UNKNOWN/PASS.

- [ ] **Step 1:** create/resolve a disposable free-tier Neon project without printing credentials.
- [ ] **Step 2:** create a MarcoPolo PostgreSQL connection using `connection_setup(type='pg')`; expected `MARCOPOLO_PG_CONNECTION_VISIBLE`.
- [ ] **Step 3:** run read-only sentinel:

```sql
SELECT current_database() AS db, current_user AS db_user, 1 AS sentinel;
```

Expected `sentinel=1`.

- [ ] **Step 4:** create probe-only table:

```sql
CREATE TABLE IF NOT EXISTS theseus_memory_probe (
  operation_id UUID PRIMARY KEY,
  event_id UUID NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- [ ] **Step 5:** generate synthetic UUIDs and insert canary with `ON CONFLICT (operation_id) DO NOTHING RETURNING ...`; canary value `MP-NEON-MEMORY-PROBE-20260906`.
- [ ] **Step 6:** exact SELECT by operation_id; only then classify `REMOTE_WRITE=PASS` and `EXACT_READBACK=PASS`.
- [ ] **Step 7:** retry identical operation_id and verify `count(*) = 1`; classify `IDEMPOTENT_RETRY=PASS`.
- [ ] **Step 8:** issue a fresh independent MarcoPolo query and read same row; classify `FRESH_INVOCATION_PERSISTENCE=PASS`. Do not promote cross-worker/remount claims without observable distinct client evidence.
- [ ] **Step 9:** write sanitized JSON receipt:

```json
{
  "schema_version": "managed-postgres-memory-probe-v0.1",
  "date": "2026-09-06",
  "backend_class": "managed_postgresql",
  "provider": "neon",
  "transport": "marcopolo_pg_connection",
  "synthetic_only": true,
  "secret_material_recorded": false,
  "results": {
    "connection_sentinel": "PASS|FAIL|INCONCLUSIVE",
    "remote_write": "PASS|FAIL|INCONCLUSIVE",
    "exact_readback": "PASS|FAIL|INCONCLUSIVE",
    "idempotent_retry": "PASS|FAIL|INCONCLUSIVE",
    "fresh_invocation_persistence": "PASS|FAIL|INCONCLUSIVE",
    "cross_client_persistence": "PASS|FAIL|UNKNOWN"
  }
}
```

Markdown companion records only observed postconditions and UNKNOWNs.

- [ ] **Step 10: Verify hygiene:**

```bash
python3 -m json.tool artifacts/issue-17/managed-postgres-probe-20260906.json >/dev/null
grep -RniE 'postgres(ql)?://|password=|api[_-]?key|token=' artifacts/issue-17/managed-postgres-probe-20260906.* && exit 1 || true
git diff --check
```

- [ ] **Step 11:** commit evidence only after verified readback; if blocked, record exact blocker as INCONCLUSIVE/UNKNOWN rather than inventing PASS.

---

### Task 4: Publish and request fresh Codex review

**Files:** none unless verification finds a correction.

**Interfaces:**
- Consumes: Tasks 1-3 commits.
- Produces: exact remote branch identity, independent readback, and fresh Codex review request.

- [ ] **Step 1: Complete verification:** focused contract test, existing skill test, bootstrap test, wiki-push test, `git diff --check`, clean `git status`.
- [ ] **Step 2:** push only `research/memory-provider-loop-17` through governed `gh-write`; no force push/history rewrite.
- [ ] **Step 3:** independently verify remote HEAD and changed files through read-only GitHub.
- [ ] **Step 4:** post `@codex review` through governed write route, noting prior findings addressed and managed-Postgres lane added.
- [ ] **Step 5:** read back review-request comment and record exact reviewed SHA when Codex responds.
