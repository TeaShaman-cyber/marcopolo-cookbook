# Scientific Verifier Runtime Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first reproducible scientific-verifier runtime slice: a locked Python 3.11-compatible `/tmp` environment with NumPy, NetworkX, SymPy, and SciPy plus an acceptance/version receipt.

**Architecture:** Canonical dependency/runtime state lives in Git under `scientific-verifier/runtime/`; generated virtualenv/cache state lives only under `/tmp`. A one-time compatibility probe resolves a Python 3.11-compatible package set, then implementation freezes the exact transitive versions and hashes into `requirements.lock`; subsequent installs use `pip --require-hashes` only.

**Tech Stack:** Bash, Python 3.11 `venv`/`pip`, NumPy, NetworkX, SymPy, SciPy, SHA-256, `flock`.

**Spec:** `docs/superpowers/specs/2026-09-17-scientific-verifier-stand-design.md`

## Global Constraints

- Do not modify system Python, system Node, existing mcporter pins, credentials, or platform-owned runtimes.
- Generated virtualenvs, wheel/download caches, traces, and receipts are not canonical Git state.
- Runtime materialization lives under `/tmp/marcopolo-scientific-verifier-<uid>/<bundle-id>/`.
- Canonical dependency state is exact-version and hash-locked after the one-time compatibility probe.
- The initial direct scientific dependencies are exactly NumPy, NetworkX, SymPy, and SciPy; no matplotlib.
- Runtime verification records Python and all four library versions.
- Failure to materialize or validate the runtime is a runtime/infrastructure failure, not a scientific verdict.

---

### Task 1: Locked Python Runtime and Atomic Cache Materialization

**Files:**
- Create: `scientific-verifier/runtime/python.env`
- Create: `scientific-verifier/runtime/requirements.in`
- Create: `scientific-verifier/runtime/requirements.lock`
- Create: `scientific-verifier/scripts/install-runtime.sh`
- Create: `scientific-verifier/scripts/ensure-runtime.sh`
- Create: `scientific-verifier/tests/test_runtime.py`

**Interfaces:**
- Consumes: host `python3` satisfying major/minor `3.11`.
- Produces: `scientific-verifier/scripts/ensure-runtime.sh -> stdout path` of a validated ephemeral virtualenv.
- Produces: `runtime/python.env` values `PYTHON_VERSION`, `RUNTIME_BUNDLE`.
- Produces: `runtime/requirements.lock` installable by `python -m pip install --require-hashes -r`.

- [ ] **Step 1: Write failing runtime contract tests**

Create `scientific-verifier/tests/test_runtime.py` with tests that require:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_contract_files_exist():
    assert (ROOT / "runtime/python.env").is_file()
    assert (ROOT / "runtime/requirements.in").is_file()
    assert (ROOT / "runtime/requirements.lock").is_file()
    assert (ROOT / "scripts/install-runtime.sh").is_file()
    assert (ROOT / "scripts/ensure-runtime.sh").is_file()


def test_requirements_in_has_only_direct_scientific_dependencies():
    rows = [
        line.strip().lower()
        for line in (ROOT / "runtime/requirements.in").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert rows == ["numpy", "networkx", "sympy", "scipy"]


def test_lock_is_hash_pinned():
    text = (ROOT / "runtime/requirements.lock").read_text()
    assert "==" in text
    assert "--hash=sha256:" in text
    for name in ("numpy", "networkx", "sympy", "scipy"):
        assert f"{name}==" in text.lower()
```

- [ ] **Step 2: Run the tests and observe RED**

Run:

```bash
python3 -m unittest discover -s scientific-verifier/tests -p 'test_*.py' -v
```

Expected: failures because the runtime files do not exist yet.

- [ ] **Step 3: Perform one-time compatibility resolution in an isolated temporary venv**

Run only under `/tmp`; do not install into system Python:

```bash
TMP="$(mktemp -d /tmp/scientific-verifier-resolve-XXXXXX)"
python3 -m venv "$TMP/venv"
"$TMP/venv/bin/python" -m pip install --upgrade pip
"$TMP/venv/bin/python" -m pip install numpy networkx sympy scipy
"$TMP/venv/bin/python" - <<'PY'
import importlib.metadata as m
import sys
print("python", sys.version.split()[0])
for name in ("numpy", "networkx", "sympy", "scipy"):
    print(name, m.version(name))
PY
```

Acceptance for the probe: imports succeed under host Python 3.11 and exact resolved versions are captured before any lock file is authored. If resolution fails, stop with `BLOCKED_RUNTIME_COMPATIBILITY`; do not weaken Python/runtime constraints silently.

- [ ] **Step 4: Freeze exact transitive requirements with hashes**

Create `scientific-verifier/runtime/requirements.in` containing exactly:

```text
numpy
networkx
sympy
scipy
```

From the successful temporary resolver environment, freeze the exact transitive version set:

```bash
"$TMP/venv/bin/python" -m pip freeze --all \
  | grep -Ev '^(pip|setuptools|wheel)==' \
  | LC_ALL=C sort > "$TMP/resolved.txt"
```

For every exact `name==version` line in `$TMP/resolved.txt`, download its distribution into `$TMP/wheels` and record one or more SHA-256 hashes:

```bash
mkdir -p "$TMP/wheels"
while IFS= read -r req; do
  "$TMP/venv/bin/python" -m pip download --no-deps --dest "$TMP/wheels" "$req"
done < "$TMP/resolved.txt"
```

Generate `scientific-verifier/runtime/requirements.lock` deterministically with a small stdlib Python script that:

```python
# algorithm contract
# 1. read exact normalized name==version rows from resolved.txt
# 2. match downloaded wheel/sdist filenames to each normalized project name
# 3. SHA-256 every matching distribution file
# 4. emit sorted rows:
#      name==version \
#          --hash=sha256:<digest> [\
#          --hash=sha256:<digest> ...]
# 5. fail if any requirement has zero matching hashes
```

Then prove the lock can seed a fresh venv without resolver freedom:

```bash
VERIFY="$TMP/verify"
python3 -m venv "$VERIFY"
"$VERIFY/bin/python" -m pip install --require-hashes \
  -r scientific-verifier/runtime/requirements.lock
```

- [ ] **Step 5: Add the runtime identity file**

Create `scientific-verifier/runtime/python.env` from the successful probe with exactly these keys:

```text
PYTHON_VERSION=3.11
RUNTIME_BUNDLE=scientific-verifier-py311-v1
```

The bundle id changes whenever the lock/runtime contract changes incompatibly.

- [ ] **Step 6: Write minimal installer and cache loader**

`scientific-verifier/scripts/install-runtime.sh` must:

```text
source runtime/python.env
verify host python3 major/minor == PYTHON_VERSION
create staging venv under /tmp
install requirements.lock with --require-hashes
verify imports + exact direct-package versions against lock
write a canonical runtime-version receipt inside the staged runtime
atomically rename the complete staged runtime to the bundle cache path
never write a venv under /workspace
```

`scientific-verifier/scripts/ensure-runtime.sh` must:

```text
use /tmp/marcopolo-scientific-verifier-<uid>/ as mode-700 cache root
reject a symlink cache root
flock per bundle
validate cached python + all four direct package versions
call install-runtime.sh only when the cache is absent/invalid
print only the validated runtime path on stdout
```

Follow the already-reviewed `mcporter/scripts/ensure-runtime.sh` pattern for ownership, mode, locking, staging, and atomic promotion rather than inventing new cache semantics.

- [ ] **Step 7: Run runtime tests and exact materialization**

Run:

```bash
python3 -m unittest discover -s scientific-verifier/tests -p 'test_*.py' -v
scientific-verifier/scripts/install-runtime.sh
CACHE="$(scientific-verifier/scripts/ensure-runtime.sh)"
"$CACHE/bin/python" - <<'PY'
import importlib.metadata as m
import sys
print("python=" + sys.version.split()[0])
for name in ("numpy", "networkx", "sympy", "scipy"):
    print(name + "=" + m.version(name))
PY
```

Expected: all tests PASS; cache path is under `/tmp`; all four imports succeed; versions match the committed lock.

- [ ] **Step 8: Commit Task 1**

```bash
git add scientific-verifier/runtime scientific-verifier/scripts scientific-verifier/tests/test_runtime.py
git commit -m "feat: add scientific verifier runtime"
```

---

### Task 2: Acceptance Canary and Runtime Receipt

**Files:**
- Create: `scientific-verifier/tests/acceptance.sh`
- Create: `scientific-verifier/scripts/runtime-receipt.py`
- Create: `scientific-verifier/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: validated cache path from `scripts/ensure-runtime.sh`.
- Produces: deterministic JSON runtime receipt on stdout from `scripts/runtime-receipt.py`.
- Produces: acceptance summary `PASS scientific-verifier-runtime ...`.

- [ ] **Step 1: Write failing receipt tests**

Extend `scientific-verifier/tests/test_runtime.py` with a subprocess test requiring the receipt JSON to contain:

```json
{
  "python": "3.11.x",
  "packages": {
    "numpy": "...",
    "networkx": "...",
    "sympy": "...",
    "scipy": "..."
  },
  "runtime_bundle": "scientific-verifier-py311-v1"
}
```

The test must assert exact keys and non-empty versions, not hard-code patch versions that are already authoritative in the committed lock.

- [ ] **Step 2: Run receipt test and observe RED**

Run:

```bash
python3 -m unittest discover -s scientific-verifier/tests -p 'test_*.py' -v
```

Expected: FAIL because `runtime-receipt.py` does not exist yet.

- [ ] **Step 3: Implement deterministic runtime receipt**

Create `scientific-verifier/scripts/runtime-receipt.py` using only stdlib plus installed package metadata. It must:

```text
read RUNTIME_BUNDLE from runtime/python.env
record sys.version major.minor.patch
record NumPy/NetworkX/SymPy/SciPy versions via importlib.metadata
emit JSON with sort_keys=True and compact separators
write no timestamps or host-specific paths in this runtime-identity receipt
```

- [ ] **Step 4: Add acceptance canary**

Create `scientific-verifier/tests/acceptance.sh` that:

```text
calls ensure-runtime.sh
asserts cache path begins /tmp/marcopolo-scientific-verifier-
asserts python major/minor == 3.11
imports numpy, networkx, sympy, scipy
runs runtime-receipt.py inside the validated runtime
parses receipt with Python stdlib JSON
asserts exact receipt keys
prints PASS scientific-verifier-runtime plus bundle and direct-package versions
```

- [ ] **Step 5: Document the stand and runtime boundary**

Create `scientific-verifier/README.md` explaining:

```text
why the stand exists: avoid model-mediated/manual glue between retrieval and verification
where it lives: /workspace/marcopolo-cookbook/scientific-verifier in canonical Git; runtime cache under /tmp
how to materialize: scripts/install-runtime.sh then scripts/ensure-runtime.sh
how to verify: tests/acceptance.sh
what is authoritative: committed lock + scripts + receipts, not an existing cache
what this slice does not yet provide: source snapshot adapter, typed projection, applicability router, or held-out prediction
relationship: uses existing mcporter/Wolfram route later; issue #4 remains separate fallback routing work
```

Add one compact link from root `README.md` to `scientific-verifier/README.md`.

- [ ] **Step 6: Run acceptance and regression tests**

Run:

```bash
scientific-verifier/tests/acceptance.sh
python3 -m unittest discover -s tests -v
rules/test-materialize-workspace-rules.sh
mcporter/tests/acceptance.sh
```

Expected: scientific verifier acceptance PASS; existing cookbook root tests PASS; rules materializer PASS; mcporter acceptance remains PASS.

- [ ] **Step 7: Commit Task 2**

```bash
git add scientific-verifier README.md
git commit -m "docs: document scientific verifier runtime"
```

- [ ] **Step 8: Verify remote postcondition after push**

Push the implementation branch, then verify through an independent GitHub read route:

```text
remote branch head == local exact commit
scientific-verifier/runtime/requirements.lock exists on remote
scientific-verifier/tests/acceptance.sh exists on remote
scientific-verifier/README.md exists on remote
```

Record the exact commit and acceptance output in cookbook issue #43. Do not merge or promote into normal workflow in this slice.
