# MarcoPolo Cookbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `/workspace/tools` into a curated private GitHub repository `TeaShaman-cyber/marcopolo-cookbook` with reviewed content, reproducible dependency boundaries, and independent remote readback.

**Architecture:** Keep `/workspace/tools` as the repository root. Add repository hygiene and a root index, explicitly exclude generated/runtime material, perform a bounded secret review before staging, create one reviewed initial commit, publish through the governed GitHub write path, and verify the exact remote state through an independent read path.

**Tech Stack:** Git, GitHub CLI/API through MarcoPolo governed `gh-write`, Bash, Python 3, existing mcporter/session-search workbench files.

**Spec:** `docs/superpowers/specs/2026-09-03-marcopolo-cookbook-design.md`

## Global Constraints

- Repository name: `marcopolo-cookbook`.
- Owner: `TeaShaman-cyber`.
- Initial visibility: private.
- Local source directory: `/workspace/tools`.
- Default branch: `main`.
- Initial import is curated; no blind `git add .` before review.
- `mcporter/node_modules/`, `__pycache__/`, `*.pyc`, virtualenvs, logs, credential material, auth caches, and unreviewed `mcporter/traces/*.json` are excluded.
- Credential-management scripts may be committed only when they contain logic/references and no embedded secrets.
- Remote publication is accepted only after independent readback of visibility, default branch, HEAD, representative includes, and representative excludes.

---

### Task 1: Repository hygiene and root index

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Test: shell/path assertions run from `/workspace/tools`

**Interfaces:**
- Consumes: approved design spec and existing component READMEs.
- Produces: repository-wide ignore contract and navigation index used by the initial commit.

- [ ] **Step 1: Write failing hygiene assertions**

```bash
cd /workspace/tools
test -f .gitignore
test -f README.md
grep -F '**/node_modules/' .gitignore
grep -F 'mcporter/traces/' .gitignore
grep -F 'marcopolo/README.md' README.md
```

Expected before implementation: at least one assertion fails because root repository files do not yet exist.

- [ ] **Step 2: Create minimal `.gitignore` and root `README.md`**

`.gitignore` must include:

```gitignore
**/node_modules/
**/__pycache__/
*.py[cod]
.venv/
venv/
.env
.env.*
*.log
.DS_Store
mcporter/traces/
```

Root README must describe the cookbook, runtime boundaries, component map, security rule, and links to `marcopolo/`, `session-search/`, `mcporter/`, `search/`, and `jester-forum/`.

- [ ] **Step 3: Re-run hygiene assertions**

Expected: PASS.

---

### Task 2: Bounded import/security review

**Files:**
- Create: `docs/import-review-2026-09-03.md`
- Inspect: all candidate text files outside ignored/generated paths

**Interfaces:**
- Consumes: repository candidate file inventory.
- Produces: explicit per-file/class disposition required before staging.

- [ ] **Step 1: Enumerate candidates without Git staging**

```bash
cd /workspace/tools
find . -type f \
  -not -path './mcporter/node_modules/*' \
  -not -path './mcporter/traces/*' \
  -not -path '*/__pycache__/*' \
  | sort
```

- [ ] **Step 2: Scan for credential-shaped content without printing values**

Use a bounded Python scanner that reports only filename, line number, and matched keyword class for patterns such as `token`, `secret`, `password`, `authorization`, `cookie`, `api_key`, private-key markers, and obvious credential assignment shapes. It must not print matched values.

- [ ] **Step 3: Manually inspect flagged files**

Inspect the source of flagged scripts and config files. Classify each reviewed candidate in `docs/import-review-2026-09-03.md` as one of:

```text
SAFE_TO_COMMIT
SAFE_AFTER_REDACTION
EXCLUDE_RUNTIME_ONLY
BLOCKED_SECRET_OR_UNKNOWN
```

- [ ] **Step 4: Verify no blocked file is eligible for staging**

Expected: every staged candidate is `SAFE_TO_COMMIT` or has completed redaction with a documented reason.

---

### Task 3: Initialize Git and create reviewed initial commit

**Files:**
- Create: `.git/`
- Stage: only approved paths from Task 2

**Interfaces:**
- Consumes: `.gitignore`, root README, import review dispositions.
- Produces: exact initial `main` commit SHA.

- [ ] **Step 1: Initialize repository**

```bash
cd /workspace/tools
git init -b main
```

- [ ] **Step 2: Stage explicit approved paths**

Use `git add -- <explicit paths>` from the approved allow-list. Do not use `git add .` for the initial staging operation.

- [ ] **Step 3: Verify excluded/runtime content is absent**

```bash
git ls-files | grep -E '(^|/)node_modules/|(^|/)__pycache__/|\.pyc$|^mcporter/traces/' && exit 1 || true
git diff --cached --check
```

- [ ] **Step 4: Run syntax/acceptance checks**

Run `bash -n` on committed Bash scripts and existing lightweight acceptance tests that do not require unavailable credentials or external mutations. Record skipped tests with reason.

- [ ] **Step 5: Commit**

```bash
git commit -m 'chore: establish MarcoPolo cookbook'
```

Record:

```bash
git rev-parse HEAD
```

---

### Task 4: Create private GitHub repository and publish exact history

**Files:**
- Modify: local Git remote configuration
- Remote create: `TeaShaman-cyber/marcopolo-cookbook`

**Interfaces:**
- Consumes: exact local initial commit SHA.
- Produces: private GitHub repository whose `main` points to the same commit/tree.

- [ ] **Step 1: Confirm repository name is not already occupied**

Use the governed GitHub context to query `TeaShaman-cyber/marcopolo-cookbook`. If it exists, stop mutation and inspect rather than overwriting.

- [ ] **Step 2: Create repository as private**

Use governed `gh-write`/GitHub API. Do not expose credentials.

- [ ] **Step 3: Publish `main`**

Prefer normal governed Git transport if it works. If smart-HTTP push returns the known 403 boundary, use the governed Git Database API with the complete local tree and exact parent/history semantics.

- [ ] **Step 4: Configure/fetch remote and compare exact SHA**

```bash
git fetch origin main
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
test "$LOCAL" = "$REMOTE"
```

---

### Task 5: Independent GitHub readback and completion receipt

**Files:**
- Create: `docs/bootstrap-receipt-2026-09-03.md`

**Interfaces:**
- Consumes: published remote repository.
- Produces: human-readable completion receipt with independently verified repository state.

- [ ] **Step 1: Read repository through independent GitHub read path**

Verify:

```text
owner/name = TeaShaman-cyber/marcopolo-cookbook
visibility = private
default branch = main
remote HEAD = intended initial commit
```

- [ ] **Step 2: Verify representative includes and excludes**

Includes must contain at least:

```text
README.md
marcopolo/README.md
session-search/README.md
mcporter/README.md
docs/superpowers/specs/2026-09-03-marcopolo-cookbook-design.md
```

Excludes must not contain:

```text
mcporter/node_modules/
__pycache__/
mcporter/traces/
```

- [ ] **Step 3: Write and commit completion receipt**

The receipt records local/remote HEAD, repository visibility, verification path, excluded runtime classes, tests executed, and any intentionally skipped checks. Publish the receipt as a second small commit and independently read that commit back as well.
