# Query-Routed Cookbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic prototype that compiles bounded task-specific context packets from exact labels, inheritance, inhibition, and stable references to existing cookbook Markdown.

**Architecture:** Keep Markdown as canonical operational content. Add a small JSON routing manifest plus a pure Python router/compiler that validates route structure, resolves matching/inhibition/inheritance, extracts exact Markdown sections, and emits normalized context packets. The first lane is deterministic only: no embeddings, fuzzy matching, LLM classification, telemetry weighting, or automatic execution.

**Tech Stack:** Python 3.11 standard library, JSON, Markdown heading parsing, unittest, existing repository shell acceptance checks.

**Spec:** `docs/superpowers/specs/2026-09-06-query-routed-cookbook-design.md`

## Global Constraints

- `schema_version` for the manifest is `cookbook-routing-v0.1`.
- `schema_version` for compiled packets is `cookbook-context-v0.1`.
- Existing Markdown remains canonical operational content in v0.1.
- The manifest MUST NOT duplicate operational rule prose.
- Routing uses exact normalized string labels only.
- Misses return explicit `route_state = UNKNOWN`; no nearest-route guessing.
- Equal-priority surviving matches are an error.
- Inheritance cycles are invalid.
- Inhibition is route-ID based in v0.1.
- Referenced Markdown headings must exist exactly once and remain inside repository root.
- `defaults.max_sections` is a hard post-inheritance/de-duplication budget; overflow returns `CONTEXT_BUDGET_EXCEEDED` without partial output.
- Routing does not grant authorization or execute operations.
- No embeddings, semantic search, dynamic telemetry weights, Skill reinstall, or automatic action execution in this plan.

---

### Task 1: Manifest schema and structural validation

**Files:**
- Create: `context-routing/routes.json`
- Create: `tools/context_router.py`
- Create: `tests/test_context_router.py`

**Interfaces:**
- Produces: `load_manifest(path: Path) -> dict[str, Any]`
- Produces: `validate_manifest(manifest: Mapping[str, Any], repo_root: Path) -> None`
- Produces: `ContextRoutingError(code: str)` carrying deterministic error codes.

- [ ] **Step 1: Write failing tests for schema, IDs, labels, references, and cycles**

Add tests equivalent to:

```python
from pathlib import Path
import json
import tempfile
import unittest

from tools.context_router import ContextRoutingError, load_manifest, validate_manifest


class ContextRouterManifestTest(unittest.TestCase):
    def test_duplicate_route_id_is_rejected(self):
        manifest = {
            "schema_version": "cookbook-routing-v0.1",
            "defaults": {"max_sections": 4, "fallback_route": "default.unknown"},
            "routes": [
                {"id": "x", "priority": 1, "match": {}, "inherits": [], "inhibits": [], "sections": []},
                {"id": "x", "priority": 2, "match": {}, "inherits": [], "inhibits": [], "sections": []},
            ],
        }
        with self.assertRaisesRegex(ContextRoutingError, "ROUTE_ID_DUPLICATE"):
            validate_manifest(manifest, Path.cwd())

    def test_missing_inheritance_target_is_rejected(self):
        manifest = {
            "schema_version": "cookbook-routing-v0.1",
            "defaults": {"max_sections": 4, "fallback_route": "default.unknown"},
            "routes": [
                {"id": "x", "priority": 1, "match": {}, "inherits": ["missing"], "inhibits": [], "sections": []}
            ],
        }
        with self.assertRaisesRegex(ContextRoutingError, "INHERIT_TARGET_MISSING"):
            validate_manifest(manifest, Path.cwd())

    def test_inheritance_cycle_is_rejected(self):
        manifest = {
            "schema_version": "cookbook-routing-v0.1",
            "defaults": {"max_sections": 4, "fallback_route": "default.unknown"},
            "routes": [
                {"id": "a", "priority": 1, "match": {}, "inherits": ["b"], "inhibits": [], "sections": []},
                {"id": "b", "priority": 1, "match": {}, "inherits": ["a"], "inhibits": [], "sections": []},
            ],
        }
        with self.assertRaisesRegex(ContextRoutingError, "INHERITANCE_CYCLE"):
            validate_manifest(manifest, Path.cwd())
```

Also cover invalid schema version, invalid label key regex, missing inhibition target, duplicate section reference in one route, repository path escape, missing file, missing heading, and heading appearing more than once.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_context_router.ContextRouterManifestTest -v
```

Expected: import or missing-function failures before production implementation exists.

- [ ] **Step 3: Implement minimal structural validator**

Implement in `tools/context_router.py`:

```python
class ContextRoutingError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ContextRoutingError("MANIFEST_INVALID")
    return value
```

Validation must use exact error codes and graph traversal for inheritance cycles. Paths must be resolved against `repo_root` and rejected if `resolved_path` is not inside `repo_root.resolve()`.

- [ ] **Step 4: Add the initial empty-safe manifest**

Create `context-routing/routes.json` with only the fallback route and defaults:

```json
{
  "schema_version": "cookbook-routing-v0.1",
  "defaults": {
    "max_sections": 4,
    "fallback_route": "default.unknown"
  },
  "routes": [
    {
      "id": "default.unknown",
      "priority": -1000,
      "match": {},
      "inherits": [],
      "inhibits": [],
      "sections": []
    }
  ]
}
```

The fallback route is reserved and is not a normal candidate route during matching.

- [ ] **Step 5: Run focused and existing regressions**

Run:

```bash
python3 -m unittest tests.test_context_router -v
python3 -m unittest discover -s tests -p 'test_*.py'
bash tests/python-bootstrap.sh
bash tests/wiki-push.sh
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add context-routing/routes.json tools/context_router.py tests/test_context_router.py
git commit -m 'research: validate cookbook routing manifest'
```

---

### Task 2: Deterministic matching, inhibition, and inheritance

**Files:**
- Modify: `tools/context_router.py`
- Modify: `tests/test_context_router.py`

**Interfaces:**
- Consumes: validated manifest from Task 1.
- Produces: `select_route(manifest: Mapping[str, Any], labels: Mapping[str, str]) -> str | None`
- Produces: `resolve_route_chain(manifest: Mapping[str, Any], route_id: str) -> list[str]`

- [ ] **Step 1: Write failing tests for exact matching**

Add:

```python
class ContextRouterSelectionTest(unittest.TestCase):
    def test_all_match_keys_are_and_and_values_are_or(self):
        manifest = manifest_with_routes([
            route("a", 10, {"surface": ["workspace_shell"], "operation": ["structured_edit", "generated_file"]}),
            route("b", 5, {"surface": ["workspace_shell"]}),
        ])
        self.assertEqual(
            select_route(manifest, {"surface": "workspace_shell", "operation": "structured_edit"}),
            "a",
        )

    def test_absent_label_does_not_match(self):
        manifest = manifest_with_routes([route("a", 10, {"operation": ["structured_edit"]})])
        self.assertIsNone(select_route(manifest, {"surface": "workspace_shell"}))
```

- [ ] **Step 2: Write failing tests for inhibition and ambiguity**

Cover:

```python
def test_inhibited_matching_route_is_removed(self):
    # governed route and unsafe route both match; governed route inhibits unsafe route.
    ...

def test_equal_priority_survivors_fail(self):
    with self.assertRaisesRegex(ContextRoutingError, "ROUTE_AMBIGUOUS"):
        select_route(...)
```

- [ ] **Step 3: Write failing tests for inheritance order and de-duplication**

Expected chain semantics:

```text
root parent -> intermediate parent -> winner
```

Multiple parents must be traversed in declared order. Duplicate route IDs in the resolved chain must not silently mask an inheritance cycle; cycles are already rejected by validation.

- [ ] **Step 4: Run selection tests and verify RED**

```bash
python3 -m unittest tests.test_context_router.ContextRouterSelectionTest -v
```

Expected: failures because route-selection functions do not yet exist.

- [ ] **Step 5: Implement matching and inhibition**

Matching rule:

```python
def route_matches(route, labels):
    return all(
        key in labels and labels[key] in allowed
        for key, allowed in route["match"].items()
    )
```

Selection algorithm must be exactly:

```text
match normal routes
-> collect inhibition edges from matching routes
-> remove inhibited route IDs
-> if none: return None
-> choose highest priority
-> if >1 survivor at highest priority: ROUTE_AMBIGUOUS
```

Fallback is not included in normal candidate matching.

- [ ] **Step 6: Implement deterministic inheritance expansion**

`resolve_route_chain()` must return ancestors root-to-leaf followed by the winning route, with deterministic parent declaration order.

- [ ] **Step 7: Run focused and full tests**

```bash
python3 -m unittest tests.test_context_router -v
python3 -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add tools/context_router.py tests/test_context_router.py
git commit -m 'research: route cookbook context deterministically'
```

---

### Task 3: Exact Markdown section extraction and context budget

**Files:**
- Modify: `tools/context_router.py`
- Modify: `tests/test_context_router.py`
- Create: `tests/fixtures/context-routing-v0.1.json`

**Interfaces:**
- Produces: `extract_section(repo_root: Path, ref: Mapping[str, str]) -> dict[str, str]`
- Produces: `compile_context(manifest, labels, repo_root) -> dict[str, Any]`
- Packet schema: `cookbook-context-v0.1`.

- [ ] **Step 1: Write failing extraction tests**

Use a temporary Markdown fixture:

```markdown
# Root
intro

## A
alpha

### A child
child

## B
beta
```

Assert that extracting `## A` includes its child subsection but stops before `## B`.

Also assert exact heading uniqueness and UTF-8 preservation.

- [ ] **Step 2: Write failing packet tests**

Matched packet must normalize to:

```python
{
    "schema_version": "cookbook-context-v0.1",
    "route_state": "MATCHED",
    "route_id": "workspace-shell.structured-edit",
    "labels": {"operation": "structured_edit", "surface": "workspace_shell"},
    "sections": [...],
}
```

Unknown packet must be:

```python
{
    "schema_version": "cookbook-context-v0.1",
    "route_state": "UNKNOWN",
    "route_id": "default.unknown",
    "labels": {"domain": "unclassified"},
    "sections": [],
}
```

- [ ] **Step 3: Write failing budget test**

A route whose inherited + own distinct references exceed `defaults.max_sections` must raise/return deterministic `CONTEXT_BUDGET_EXCEEDED` before returning any partial section list.

- [ ] **Step 4: Run compile tests and verify RED**

```bash
python3 -m unittest tests.test_context_router.ContextRouterCompileTest -v
```

- [ ] **Step 5: Implement Markdown section extraction**

Heading termination rule:

```text
start at exact heading
include following lines
stop before next heading whose level <= selected heading level
or EOF
```

Do not use a Markdown dependency; parse headings with a small deterministic standard-library routine.

- [ ] **Step 6: Implement context compilation**

Algorithm:

```text
select route
if no match -> UNKNOWN packet
resolve inheritance chain
concatenate section refs chain order
stable de-duplicate refs
check max_sections before extraction
extract exact sections
emit normalized packet
```

- [ ] **Step 7: Add fixture-exact cases**

Create `tests/fixtures/context-routing-v0.1.json` containing at least:

- structured workspace edit;
- simple direct CLI operation;
- GitHub mutation;
- GitHub read;
- unknown task;
- context budget overflow expected error.

Fixture expected values should identify route state, route ID, and ordered section references. Full prose content does not need duplication inside the fixture; tests compare extracted section identity and separately validate content against Markdown.

- [ ] **Step 8: Run focused/full gates and commit**

```bash
python3 -m unittest tests.test_context_router -v
python3 -m unittest discover -s tests -p 'test_*.py'
git diff --check
git add tools/context_router.py tests/test_context_router.py tests/fixtures/context-routing-v0.1.json
git commit -m 'research: compile bounded cookbook context packets'
```

---

### Task 4: Add real v0.1 cookbook routes without duplicating prose

**Files:**
- Modify: `context-routing/routes.json`
- Modify: `tests/fixtures/context-routing-v0.1.json`
- Modify: `tests/test_context_router.py`

**Interfaces:**
- Consumes: exact existing headings from `marcopolo/README.md`.
- Produces: real initial routes for shell language choice, GitHub read/write authority, and postcondition/readback guidance.

- [ ] **Step 1: Inventory exact canonical headings before editing manifest**

Run:

```bash
rg -n '^## |^### ' marcopolo/README.md
```

Use only headings that exist exactly once. Do not rewrite Markdown merely to make routing easier unless a stale/ambiguous heading proves unavoidable.

- [ ] **Step 2: Write failing route fixture expectations**

Fixture must expect:

```text
workspace_shell + structured_edit
-> workspace-shell.structured-edit
-> shell execution-language/quoting sections
-> inherited postcondition guidance

workspace_shell + direct_cli
-> workspace-shell.direct-cli
-> no structured-edit-only section

github + mutation
-> github.mutation-governed
-> READ/WRITE asymmetry + governed-write/readback guidance
-> unsafe direct mutation route inhibited

github + read
-> github.read
-> no write-only procedure section
```

- [ ] **Step 3: Add the smallest real manifest route graph**

Manifest should contain conceptual route IDs similar to:

```text
marcopolo.global
default.unknown
workspace-shell.direct-cli
workspace-shell.structured-edit
workspace-shell.inline-complex-shell
github.read
github.mutation-direct
github.mutation-governed
```

`github.mutation-governed` must inhibit `github.mutation-direct` when both match. The unsafe/direct route exists only to prove inhibition mechanics; it must never win the fixture.

- [ ] **Step 4: Validate manifest against real Markdown**

```bash
python3 tools/context_router.py validate --manifest context-routing/routes.json --repo-root .
```

If the CLI does not yet exist, call the validation function from a one-line Python command for this task and leave CLI creation to Task 5.

Expected: PASS with zero stale/ambiguous references.

- [ ] **Step 5: Run fixture-exact tests twice for determinism**

```bash
python3 -m unittest tests.test_context_router -v
python3 -m unittest tests.test_context_router -v
```

Canonical serialized packets from the two runs must be byte-identical for the same inputs.

- [ ] **Step 6: Run repository regressions and commit**

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
bash tests/python-bootstrap.sh
bash tests/wiki-push.sh
git diff --check
git add context-routing/routes.json tests/fixtures/context-routing-v0.1.json tests/test_context_router.py
git commit -m 'research: route initial MarcoPolo cookbook rules'
```

---

### Task 5: Thin CLI, human documentation, and prototype acceptance

**Files:**
- Modify: `tools/context_router.py`
- Create: `context-routing/README.md`
- Modify: `README.md`
- Modify: `tests/test_context_router.py`

**Interfaces:**
- Produces CLI:
  - `python3 tools/context_router.py validate --manifest context-routing/routes.json --repo-root .`
  - `python3 tools/context_router.py compile --manifest context-routing/routes.json --repo-root . --labels-json '{...}'`
- CLI stdout for `compile` is one canonical JSON packet; diagnostics/errors go to stderr with non-zero exit.

- [ ] **Step 1: Write failing CLI tests**

Use `subprocess.run([...], shell=False, capture_output=True, text=True)` and assert:

- `validate` exits 0 for canonical manifest;
- stale fixture exits non-zero with exact error code;
- `compile` emits parseable `cookbook-context-v0.1` JSON;
- unknown labels emit `UNKNOWN`, not a guessed route;
- CLI accepts labels only as JSON data and never executes label contents.

- [ ] **Step 2: Run CLI tests and verify RED**

```bash
python3 -m unittest tests.test_context_router.ContextRouterCliTest -v
```

- [ ] **Step 3: Implement minimal argparse CLI**

Use only standard library `argparse`. Canonical output:

```python
print(json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
```

No operation execution belongs in the CLI.

- [ ] **Step 4: Document the prototype boundary**

`context-routing/README.md` must state:

```text
Markdown = canonical operational content
routes.json = deterministic routing/index state
context packet = compiled execution view
```

Document exact-label input, UNKNOWN semantics, inhibition, inheritance, hard section budget, and that telemetry-backed dynamic weights are future research only.

Root `README.md` gets one short link to `context-routing/README.md`; do not expand the root index into another full guide.

- [ ] **Step 5: Run acceptance matrix**

Run:

```bash
python3 tools/context_router.py validate --manifest context-routing/routes.json --repo-root .
python3 tools/context_router.py compile --manifest context-routing/routes.json --repo-root . --labels-json '{"surface":"workspace_shell","operation":"structured_edit"}'
python3 tools/context_router.py compile --manifest context-routing/routes.json --repo-root . --labels-json '{"domain":"github","operation":"mutation"}'
python3 tools/context_router.py compile --manifest context-routing/routes.json --repo-root . --labels-json '{"domain":"unclassified"}'
python3 -m unittest discover -s tests -p 'test_*.py'
bash tests/python-bootstrap.sh
bash tests/wiki-push.sh
git diff --check
```

Expected:

```text
manifest validation                PASS
structured-edit route              MATCHED
GitHub mutation governed route     MATCHED
unknown route                      UNKNOWN
stale reference escape rate        0
ambiguous route escape rate        0
inhibition failure rate            0
context budget violation escape    0
all repository tests               PASS
```

- [ ] **Step 6: Verify no accidental prose duplication**

Inspect `context-routing/routes.json` and confirm section entries contain only path/heading identities and routing metadata, not copied cookbook rule bodies.

- [ ] **Step 7: Commit final prototype**

```bash
git add tools/context_router.py context-routing/README.md README.md tests/test_context_router.py
git commit -m 'research: expose query-routed cookbook prototype'
```

- [ ] **Step 8: Publish and request review through governed GitHub route**

Use the repository's established governed `gh-write` path for branch publication/PR creation. Independently read back the resulting branch/PR with the read-only GitHub connector before claiming publication.

Review request should ask specifically whether:

- manifest remains index-only rather than duplicated authority;
- route ambiguity/inhibition/inheritance semantics are deterministic;
- Markdown extraction can silently drift;
- the section-count budget is a sufficient first boundedness control;
- UNKNOWN/fail-closed behavior prevents guessed operational guidance.

---

## Self-review checklist

- Every normative v0.1 requirement in the design is assigned to a task.
- No task introduces semantic retrieval, embeddings, telemetry weighting, or auto-execution.
- Manifest content remains routing/index metadata only.
- All mutations happen only after RED tests for the behavior being introduced.
- Every task ends in an independently reviewable commit.
- Final publication uses governed GitHub write and independent readback.
