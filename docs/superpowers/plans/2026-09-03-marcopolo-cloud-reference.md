# MarcoPolo Cloud Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a passive cloud-reference layer that identifies hosting evidence for public MarcoPolo endpoints, queries reviewed anonymous reference MCPs, preserves uncertainty, and emits reproducible JSON receipts.

**Architecture:** The implementation is split into four independent wrappers under `cloud-reference/bin`: passive hosting collection, reviewed cloud documentation lookup, WAF-reference lookup, and registry/source health checks. All wrappers share a typed receipt envelope and never infer provider authority from one heuristic signal. The initial target is `mcp.marcopolo.dev`; connector/control-plane failures remain distinct from target HTTP failures.

**Tech Stack:** POSIX shell wrappers, Python 3 standard library for deterministic JSON and passive network probes, existing repo-local `mcporter` 0.9.0, jq when present, existing Git/GitHub governed write/readback workflow.

**Spec:** `docs/superpowers/specs/2026-09-03-marcopolo-cloud-reference-design.md`

## Global Constraints

- Reference and diagnostics only; no WAF evasion, authentication bypass, automatic MCP attachment, or routing mutation.
- Every wrapper emits JSON to stdout and typed non-zero failures to stderr/exit status.
- `LIKELY_PROVIDER` requires at least two independent evidence classes.
- `VERIFIED_PROVIDER` requires a provider-owned authoritative signal in addition to converging evidence.
- Connector/control-plane failures must not be reported as target failures.
- Only `REVIEWED_REFERENCE_SOURCE` entries may be used by reference wrappers.
- No credentials, authorization headers, raw private payloads, runtime caches, or unbounded response bodies are committed.
- Acceptance tests are one-command and non-interactive.

---

### Task 1: Shared receipt schema and deterministic helpers

**Files:**
- Create: `cloud-reference/schemas/evidence-receipt.schema.json`
- Create: `cloud-reference/lib/evidence.py`
- Create: `cloud-reference/tests/test_evidence.py`

**Interfaces:**
- Produces: `new_receipt(target, probe_kind, observation_time=None) -> dict`
- Produces: `add_observation(receipt, evidence_class, source, value, authority="observed") -> dict`
- Produces: `classify_provider(receipt) -> tuple[str, float]`
- Produces: `bounded_sha256(data: bytes) -> str`

- [ ] **Step 1: Write failing unit tests for the receipt envelope and classification floor**

```python
import sys
sys.path.insert(0, "cloud-reference/lib")
from evidence import new_receipt, add_observation, classify_provider


def test_single_signal_cannot_be_likely():
    receipt = new_receipt("mcp.marcopolo.dev", "hosting-identify", "2026-09-03T00:00:00Z")
    add_observation(receipt, "http_header", "target", {"server": "example"})
    classification, confidence = classify_provider(receipt)
    assert classification == "INSUFFICIENT_EVIDENCE"
    assert confidence < 0.5


def test_two_independent_matching_signals_can_be_likely():
    receipt = new_receipt("mcp.marcopolo.dev", "hosting-identify", "2026-09-03T00:00:00Z")
    add_observation(receipt, "dns", "target", {"provider_candidate": "vercel"})
    add_observation(receipt, "http_header", "target", {"provider_candidate": "vercel"})
    classification, confidence = classify_provider(receipt)
    assert classification == "LIKELY_PROVIDER"
    assert confidence >= 0.5
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python3 -m unittest cloud-reference/tests/test_evidence.py -v`
Expected: import/module failure because implementation does not exist.

- [ ] **Step 3: Implement the minimal deterministic receipt helper and schema**

Implementation requirements:
- receipt fields exactly match the design envelope;
- observations are append-only dictionaries with explicit `evidence_class`, `source`, `value`, `authority`;
- raw hashes are `sha256:<64 lowercase hex>`;
- classification counts unique evidence classes, not repeated observations from one class;
- no heuristic-only path returns `VERIFIED_PROVIDER`.

- [ ] **Step 4: Run tests and JSON-schema parse checks**

Run: `python3 -m unittest cloud-reference/tests/test_evidence.py -v && python3 -m json.tool cloud-reference/schemas/evidence-receipt.schema.json >/dev/null`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cloud-reference/schemas/evidence-receipt.schema.json cloud-reference/lib/evidence.py cloud-reference/tests/test_evidence.py
git commit -m "feat: add cloud reference evidence model"
```

### Task 2: Passive `hosting-identify` wrapper

**Files:**
- Create: `cloud-reference/bin/hosting-identify`
- Create: `cloud-reference/lib/hosting.py`
- Create: `cloud-reference/tests/test_hosting.py`
- Modify: `cloud-reference/README.md`

**Interfaces:**
- Consumes: receipt helpers from Task 1.
- Produces: `collect_dns(hostname) -> list[dict]`
- Produces: `collect_tls(hostname, port=443, timeout=5) -> dict`
- Produces: `collect_http(hostname, timeout=5, body_limit=4096) -> dict`
- CLI: `cloud-reference/bin/hosting-identify HOSTNAME [--label LABEL] [--timeout SECONDS]`

- [ ] **Step 1: Write failing tests for hostname validation and provider-classification invariants**

```python
import sys
sys.path.insert(0, "cloud-reference/lib")
from hosting import validate_hostname


def test_rejects_url_and_shell_text():
    for value in ["https://mcp.marcopolo.dev", "mcp.marcopolo.dev;id", "mcp.marcopolo.dev/path"]:
        try:
            validate_hostname(value)
        except ValueError:
            pass
        else:
            raise AssertionError(value)


def test_accepts_public_hostname_shape():
    assert validate_hostname("mcp.marcopolo.dev") == "mcp.marcopolo.dev"
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest cloud-reference/tests/test_hosting.py -v`
Expected: import/module failure.

- [ ] **Step 3: Implement bounded passive DNS/TLS/HTTP collection**

Implementation requirements:
- use Python standard library only;
- DNS via `socket.getaddrinfo` plus `dig`/`nslookup` only when present for CNAME enrichment;
- TLS via `ssl.create_default_context` and certificate metadata only;
- HTTP GET/HEAD bounded to 4096 bytes, no cookies/auth headers, redirects recorded explicitly;
- selected safe headers only: `server`, `via`, `x-vercel-id`, `cf-ray`, `cf-cache-status`, `x-powered-by`, `x-request-id`, `fly-request-id` when present;
- error-page body stored only as bounded SHA256 plus at most a sanitized short diagnostic excerpt;
- failures typed as `TARGET_DNS_ERROR`, `TARGET_TLS_ERROR`, `TARGET_HTTP_ERROR`, or `LOCAL_RUNTIME_ERROR`.

- [ ] **Step 4: Run unit tests and one passive live probe**

Run:
```bash
python3 -m unittest cloud-reference/tests/test_hosting.py -v
cloud-reference/bin/hosting-identify mcp.marcopolo.dev > /tmp/marcopolo-hosting.json
python3 -m json.tool /tmp/marcopolo-hosting.json >/dev/null
```
Expected: tests PASS; probe emits valid receipt regardless of whether target evidence is conclusive.

- [ ] **Step 5: Commit**

```bash
git add cloud-reference/bin/hosting-identify cloud-reference/lib/hosting.py cloud-reference/tests/test_hosting.py cloud-reference/README.md
git commit -m "feat: add passive hosting identification"
```

### Task 3: Reviewed reference-source registry

**Files:**
- Create: `cloud-reference/queries/reviewed-sources.json`
- Create: `cloud-reference/lib/sources.py`
- Create: `cloud-reference/tests/test_sources.py`

**Interfaces:**
- Produces: `load_reviewed_sources(path) -> list[dict]`
- Produces source states: `DISCOVERED`, `LIVE_METADATA_VERIFIED`, `ANONYMOUS_EXECUTION_VERIFIED`, `REVIEWED_REFERENCE_SOURCE`.

- [ ] **Step 1: Write failing tests that reject unreviewed sources from execution**

```python
import sys
sys.path.insert(0, "cloud-reference/lib")
from sources import executable_sources


def test_only_reviewed_sources_are_executable():
    sources = [
        {"name": "a", "state": "DISCOVERED"},
        {"name": "b", "state": "REVIEWED_REFERENCE_SOURCE"},
    ]
    assert [s["name"] for s in executable_sources(sources)] == ["b"]
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest cloud-reference/tests/test_sources.py -v`
Expected: import/module failure.

- [ ] **Step 3: Implement source validation and seed only already reviewed sources**

Seed records must include name, endpoint, intended domain, state, last verified date, and evidence note for sources already observed in this research, initially including official Cloudflare Docs MCP, AWS Knowledge MCP, Microsoft Learn MCP, and Context7 only when their reviewed execution evidence is available.

- [ ] **Step 4: Run tests and JSON validation**

Run: `python3 -m unittest cloud-reference/tests/test_sources.py -v && python3 -m json.tool cloud-reference/queries/reviewed-sources.json >/dev/null`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cloud-reference/queries/reviewed-sources.json cloud-reference/lib/sources.py cloud-reference/tests/test_sources.py
git commit -m "feat: register reviewed cloud reference sources"
```

### Task 4: `mcp-registry-check` and reference wrappers

**Files:**
- Create: `cloud-reference/bin/mcp-registry-check`
- Create: `cloud-reference/bin/cloud-docs`
- Create: `cloud-reference/bin/waf-reference`
- Create: `cloud-reference/lib/mcp.py`
- Create: `cloud-reference/tests/test_mcp.py`

**Interfaces:**
- Consumes reviewed-source registry from Task 3 and repo-local `mcporter`.
- CLI: `mcp-registry-check SOURCE_NAME`
- CLI: `cloud-docs PROVIDER QUERY`
- CLI: `waf-reference PROVIDER OBSERVATION`

- [ ] **Step 1: Write failing tests for command construction and defensive query boundaries**

```python
import sys
sys.path.insert(0, "cloud-reference/lib")
from mcp import build_reference_query


def test_waf_reference_rejects_bypass_intent():
    try:
        build_reference_query("cloudflare", "how to bypass waf filtering", mode="waf")
    except ValueError:
        pass
    else:
        raise AssertionError("bypass query must be rejected")


def test_waf_reference_accepts_false_positive_diagnostics():
    query = build_reference_query("cloudflare", "documented causes of false-positive 403 filtering", mode="waf")
    assert "false-positive" in query
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest cloud-reference/tests/test_mcp.py -v`
Expected: import/module failure.

- [ ] **Step 3: Implement deterministic mcporter command construction**

Requirements:
- use repo-local `/workspace/tools/mcporter/bin/mcporter` or path relative to repository root;
- never inject raw shell fragments from user query;
- subprocess argv list only;
- timeout bounded;
- raw response hashed before compact derivation;
- auth-required/protocol-drift/connector errors remain typed;
- `waf-reference` blocks bypass/evasion intent and only permits defensive diagnostic/documentation queries.

- [ ] **Step 4: Exercise at least two reviewed anonymous reference sources**

Run bounded canaries against two currently live reviewed sources selected from Cloudflare Docs, AWS Knowledge, Microsoft Learn, or Context7. Save only sanitized derived receipts under `/tmp`; do not commit raw responses.
Expected: two successful anonymous reference calls or typed runtime drift evidence for any source that changed.

- [ ] **Step 5: Commit**

```bash
git add cloud-reference/bin/mcp-registry-check cloud-reference/bin/cloud-docs cloud-reference/bin/waf-reference cloud-reference/lib/mcp.py cloud-reference/tests/test_mcp.py
git commit -m "feat: add reviewed MCP reference wrappers"
```

### Task 5: Benign payload-shape A/B observation

**Files:**
- Create: `cloud-reference/bin/payload-shape-canary`
- Create: `cloud-reference/tests/test_payload_shape.py`
- Modify: `docs/field-notes/cloud-reference.md`

**Interfaces:**
- CLI: `payload-shape-canary`
- Produces a local JSON observation comparing semantically harmless command shapes; never attempts to transform blocked security-sensitive content.

- [ ] **Step 1: Write failing tests for the allowed canary corpus**

Corpus consists only of harmless operations such as printing a constant, reading a public file path, or invoking a harmless version command. Tests assert no corpus string contains credential markers, exploit syntax, or bypass terms.

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest cloud-reference/tests/test_payload_shape.py -v`
Expected: import/module failure.

- [ ] **Step 3: Implement representation-only A/B cases**

Examples may compare:
- one short POSIX command vs two equivalent sequential commands;
- direct literal vs a prewritten harmless file;
- simple quoting variants that do not alter semantics.

Stop after enough observations exist to classify either `NO_DIFFERENCE_OBSERVED`, `PAYLOAD_SHAPE_SENSITIVE_CONTROL_PLANE_FILTERING`, or `INCONCLUSIVE`.

- [ ] **Step 4: Run the bounded canary through MarcoPolo control plane and record only sanitized outcomes**

No repeated retries after a classification threshold is reached. A connector 403 before execution is recorded as `CONNECTOR_CONTROL_PLANE_BLOCKED`, not target failure.

- [ ] **Step 5: Commit**

```bash
git add cloud-reference/bin/payload-shape-canary cloud-reference/tests/test_payload_shape.py docs/field-notes/cloud-reference.md
git commit -m "test: add benign payload shape canary"
```

### Task 6: Initial MarcoPolo hosting receipt and issue routing

**Files:**
- Create: `docs/research/hosting-evidence/2026-09-03-mcp-marcopolo-dev.md`
- Create: `cloud-reference/receipts/README.md`
- Create only if sanitized and stable: `cloud-reference/receipts/2026-09-03-mcp-marcopolo-dev.json`
- Modify: `cloud-reference/README.md`

**Interfaces:**
- Consumes results from Tasks 2, 4, and 5.
- Produces a human-readable evidence note plus machine-readable receipt when safe to publish.

- [ ] **Step 1: Re-run passive hosting-identify after wrappers are complete**

Run: `cloud-reference/bin/hosting-identify mcp.marcopolo.dev > /tmp/marcopolo-hosting-final.json`
Expected: valid JSON receipt.

- [ ] **Step 2: Query provider-specific official documentation only for candidates actually observed**

For each candidate provider, use `cloud-docs`/`waf-reference` against reviewed sources. Do not query unrelated providers simply to manufacture corroboration.

- [ ] **Step 3: Produce final classification and uncertainty note**

The note must explicitly separate DNS/network edge, proxy/CDN layer, application hosting, and connector-provider control plane when evidence suggests multiple layers.

- [ ] **Step 4: Publish sanitized findings to the correct issues**

- Observatory #4: reference MCP health/capability changes only.
- Observatory #6: cloud-adjacent hosting/reference surfaces and provider evidence.
- `marcopolo-cookbook`: MarcoPolo-specific hosting/403/payload findings.

Use governed GitHub write and independent native GitHub readback. If write is blocked, preserve local receipt and classify publication as blocked rather than absent.

- [ ] **Step 5: Commit final documentation/receipt**

```bash
git add cloud-reference/README.md cloud-reference/receipts docs/research/hosting-evidence/2026-09-03-mcp-marcopolo-dev.md
git commit -m "docs: record MarcoPolo hosting evidence"
```

### Task 7: One-command acceptance and publication verification

**Files:**
- Create: `cloud-reference/tests/acceptance.sh`
- Modify: `README.md`

**Interfaces:**
- Produces one non-interactive acceptance command covering schema parse, unit tests, shell syntax, wrapper `--help`, forbidden-path scan, and one passive live probe.

- [ ] **Step 1: Write acceptance script with explicit gates**

Required gates:
- all Python unit tests PASS;
- JSON files parse;
- `sh -n` passes all shell wrappers;
- live passive `hosting-identify mcp.marcopolo.dev` returns JSON;
- no committed `.env`, `.vercel`, node_modules, caches, logs, or raw traces;
- no secret markers in staged/public files;
- `git diff --check` PASS.

- [ ] **Step 2: Run acceptance**

Run: `cloud-reference/tests/acceptance.sh`
Expected: final line `PASS cloud-reference acceptance`.

- [ ] **Step 3: Commit**

```bash
git add cloud-reference/tests/acceptance.sh README.md
git commit -m "test: add cloud reference acceptance gate"
```

- [ ] **Step 4: Push with governed credentials and verify exact SHA**

Use explicit `GH_CONFIG_DIR=/workspace/.config/gh-write` for Git operations. Verify local HEAD equals remote branch SHA.

- [ ] **Step 5: Independently read back representative files and issues through native GitHub connector**

Acceptance is not complete until native readback observes the exact published commit and representative receipt/documentation bytes.
