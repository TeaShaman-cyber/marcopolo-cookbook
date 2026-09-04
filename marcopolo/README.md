# MarcoPolo / Workspace Shell Field Notes

Operational runbook distilled from real Theseus sessions. It covers **failure modes actually observed** in MarcoPolo, `workspace_shell`, Git/GitHub routing, worktrees, artifacts, runtimes, and MCP client setup.

The goal is to identify **which layer actually failed**, use the smallest safe workaround, and independently read back the result before accepting it.

## Quick rules

1. **Assume `workspace_shell` may execute through `/bin/sh`, not Bash.** If Bash syntax matters, invoke `bash -lc` explicitly.
2. **A MarcoPolo timeout or `502` is an observation/control-plane failure, not proof that the target job failed.** Re-read the target system separately.
3. **Conversation runtime, MarcoPolo workspace, and GitHub Actions runner are different environments.** Never infer path or package availability across them.
4. **GitHub read and write paths can have different authority.** Native GitHub readback may work while writes fail; governed `gh-write` in MarcoPolo is the established write fallback.
5. **Never infer experiment identity from `GITHUB_SHA` after a launcher checks out another commit.** Pass experiment and launcher identities explicitly.
6. **Do not trust a successful mutation until exact remote readback.** A stale API response or incomplete Git tree can otherwise make a successful-looking write wrong.
7. **Do not assume `mcporter`, Node modules, Python packages, or prior virtualenvs persist.** Pin dependencies and record runtime versions in receipts.
8. **Search miss != absence; registry metadata != live capability; workflow success != verified evidence.** Preserve raw observations and derived conclusions separately.

---

## Runtime map: three environments that are easy to accidentally merge

```text
ChatGPT conversation runtime
  typical temporary files: /mnt/data

          !=

MarcoPolo persistent workspace
  workspace: /workspace

          !=

GitHub Actions runner
  ephemeral checkout + runner filesystem
```

A GitHub artifact downloaded through the native GitHub connector can appear under `/mnt/data` and still be invisible to MarcoPolo, because MarcoPolo executes in `/workspace` on another runtime.

**Rule:** identify which runtime produced a path before using it. If bytes must cross a boundary, explicitly materialize/copy/download them in the destination runtime. One environment not seeing another environment's file is not evidence of data loss.

---

## 1. `/bin/sh` is not Bash

### Observed symptom

```text
sh: 1: set: Illegal option -o pipefail
```

A `workspace_shell` command used `set -euo pipefail` assuming Bash. The connector executed it through `/bin/sh`, where `pipefail` was unsupported.

### Safe pattern

```bash
bash -lc 'set -euo pipefail
# bounded commands here
'
```

This also applies to `[[ ... ]]`, Bash regex matching, arrays, and other Bash-only constructs.

If failure occurs before a write step, record **no remote mutation occurred** instead of treating remote state as uncertain.

---

## 2. Nested shell quoting and heredocs are a failure domain

### Observed symptoms

- A GitHub PR body acquired a stray leading `$` due to shell quoting; independent PR readback caught it.
- While writing this README, a quoted heredoc was nested inside an outer `bash -lc '...'`. The quote/heredoc boundary broke and the shell started interpreting Markdown lines as commands. The partial result was discarded and rewritten without the competing quote layer.

### Safer pattern

```bash
cat > /tmp/body.md <<'EOF_BODY'
Markdown with $variables, backticks, and code fences stays literal here.
EOF_BODY

gh pr edit 123 --body-file /tmp/body.md
```

For large generated text, prefer a programmatic file write or a single interpolation-free payload rather than stacking `bash -lc` + heredoc + Markdown fences.

**Verification:** read the resulting file/issue/PR/comment back after write. For files, also hash them.

---

## 3. `workspace_shell` timeout != underlying process failure

Observed examples include broad recursive filesystem searches hitting the default timeout and long polling commands combining `sleep` with a later GitHub query.

A timeout establishes only:

```text
observer did not finish inside the allowed window
```

It does **not** establish:

```text
target process failed
```

### Better pattern

```text
short query → return
short query → return
artifact/readback when complete
```

Narrow filesystem scope before increasing timeout. Do not use a giant tool timeout to emulate a background worker.

---

## 4. MarcoPolo `502` during polling is an observation failure

Long `workspace_shell` polling around GitHub Actions returned `502` while the GitHub workflow itself continued normally.

```text
MarcoPolo/control-plane read failed
                !=
GitHub Actions job failed
```

Use short independent reads of the authoritative target: native GitHub job state, `gh run view` when appropriate, and artifact/receipt readback after completion.

Never assign a scientific failure disposition from a connector `502` alone.

---

## 5. GitHub READ and WRITE authority are asymmetric

The native GitHub connector has repeatedly worked for reads while some writes returned:

```text
403 Resource not accessible by integration
```

The governed MarcoPolo credential could still perform specific writes.

### Established routing

```text
READ
  native ChatGPT GitHub connector

WRITE
  MarcoPolo governed gh-write
  GH_CONFIG_DIR=/workspace/.config/gh-write

READBACK
  native ChatGPT GitHub connector
```

The native read path can itself become unavailable mid-session even after successful reauthorization. Classify that separately:

```text
native connector unavailable
  != prior write failed
  != repository permission changed
```

Readback fallback ladder for public repositories:

```text
1. native GitHub connector
2. independent public/unauthenticated GitHub read
3. governed gh + exact remote ref fetch
   (degraded independence; record this explicitly)
```

Do not replay a mutation merely because the preferred readback tool disappeared. Verify the exact remote SHA/object through the strongest remaining read path and record which authority class supplied the evidence.

Never print, inspect, or copy credential material. Use the configured credential directory without exposing secrets.

---

## 6. Ordinary `git push` can fail while GitHub API writes still work

Smart-HTTP `git push` from MarcoPolo began returning HTTP `403`, even though issue comments and GitHub API mutations through governed `gh-write` still worked.

### Fallback used successfully

```text
blob(s)
  ↓
tree
  ↓
commit
  ↓
ref update
  ↓
independent fetch/readback
```

### Required postcondition

```bash
git fetch origin <branch>
REMOTE=$(git rev-parse origin/<branch>)
test "$REMOTE" = "$EXPECTED_SHA"
```

Then run the relevant full tests on the exact published SHA.

---

## 7. Shell variables do not automatically cross into Python subprocess logic

A publication helper expected `REPO` / `BRANCH` inside Python, but the shell variables had not been exported. It failed before remote mutation.

Pass cross-process inputs explicitly:

```bash
export REPO BRANCH
python3 script.py
```

or use explicit CLI arguments. On pre-mutation failure, verify remote ref stayed unchanged before retrying.

---

## 8. Verify the actual remote parent before constructing an API commit

A local commit existed but had never been published, while the remote branch still pointed to an older commit.

Before mutation:

```bash
git fetch origin <branch>
git rev-parse HEAD
git rev-parse origin/<branch>
```

Never assume local `HEAD` means current remote branch authority.

---

## 9. GitHub read-after-write can briefly be stale

After a Git Database API ref update:

- `git fetch` saw the new remote commit;
- an immediate `gh api` ref read returned the old SHA;
- trusting the stale response briefly pushed local state toward the old head.

### Recovery

1. stop further mutation;
2. independently query/fetch the ref again;
3. compare multiple authoritative observations;
4. synchronize to the confirmed remote-tracking ref;
5. rerun the full test gate.

Do not force-push a suspected race before actual remote state is known.

---

## 10. Git Database API tree construction can accidentally delete files

An API-created commit was valid as a commit object but its tree accidentally omitted:

```text
scripts/build_realistic_sft_dataset.py
```

A fresh full test run on the published SHA caught it.

### Rule

Construct the new tree from the **complete parent tree** and overlay only intended changes. Do not substitute a sparse changed-file list for the entire tree.

A commit existing is not evidence that its repository tree is correct.

---

## 11. `git ls-remote origin` before checkout has no `origin`

Observed Actions failure:

```text
fatal: 'origin' does not appear to be a git repository
```

The launcher tried to verify a branch before checkout, so no local remote named `origin` existed.

Use the explicit repository URL:

```bash
REMOTE_SHA=$(git ls-remote \
  "https://github.com/${GITHUB_REPOSITORY}.git" \
  refs/heads/experiment/needle-realistic-sft-spec \
  | awk '{print $1}')
```

---

## 12. Shell glob is not a reliable SHA validator

The first 40-character SHA guard rejected a valid SHA and produced:

```text
BLOCKED_INVALID_SHA
```

Accepted Bash form:

```bash
if [[ ! "$REQUESTED_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo BLOCKED_INVALID_SHA
  exit 2
fi
```

This requires Bash; see section 1.

---

## 13. `GITHUB_SHA` is launcher identity, not checked-out experiment identity

A manual workflow ran from `main`, then checked out an experiment commit. `GITHUB_SHA` remained the launcher workflow commit on `main`.

The resource receipt therefore recorded the launcher SHA as experiment source even though the intended experiment commit had actually executed.

### Accepted contract

```yaml
env:
  EXPERIMENT_SHA: ${{ inputs.experiment_sha }}
  LAUNCHER_SHA: ${{ github.sha }}
```

Then:

```bash
test "$(git rev-parse HEAD)" = "$EXPERIMENT_SHA"
```

Receipt identity must distinguish:

```text
experiment_commit
launcher_commit
workflow_run_id
```

Never infer experiment identity from `GITHUB_SHA` in this architecture.

---

## 14. A new `workflow_dispatch` workflow on an experiment branch may not be invokable

A manual workflow added only on the experiment branch could not be dispatched by name:

```text
could not find any workflows named ...
```

Adding a `push` trigger was rejected because the experiment was manual-only.

### Accepted architecture

```text
small manual launcher on default branch (`main`)
        ↓
validate exact allowed experiment SHA
        ↓
checkout exact SHA
        ↓
run fixed entrypoint from experiment code
```

---

## 15. Generated files are not durable evidence until uploaded

A workflow generated receipts/logs/metrics on the Actions runner but the launcher initially did not upload them as an artifact.

```text
create
→ hash
→ upload artifact
→ read artifact metadata
→ download independently
→ re-hash
```

Workflow `success` is not a substitute for durable evidence.

---

## 16. Worktree metadata can outlive the directory

`git worktree list` referenced a worktree whose directory no longer existed:

```text
cd: can't cd to .../stage-b-full-launcher
```

Safe recovery starts with inspection:

```bash
git worktree list
git worktree prune
git branch -vv
```

Do not delete/reset a branch merely because its old worktree directory disappeared.

---

## 17. Existing branch != existing usable worktree

Observed:

```text
fatal: a branch named 'infra/stage-b-full-launcher' already exists
```

Treat these as separate state:

```text
branch ref
worktree registration
worktree directory
```

Inspect all three before create/prune/delete/reset.

---

## 18. Unknown/untracked files in an experiment worktree are a stop signal

An experiment worktree contained untracked quality-layer files and had advanced beyond the expected HEAD. Work paused rather than overwriting possible parallel work.

### Pre-edit checklist

```bash
git status --short
git rev-parse HEAD
git branch --show-current
git fetch origin <branch>
git rev-parse origin/<branch>
```

If unexpected files or commits appear, establish their origin before reset/rebase/edit.

---

## 19. Python/package compatibility differs across MarcoPolo and CI

MarcoPolo was on Python 3.11 while SciPy 1.18.x required Python >= 3.12. The intended version could not be installed locally, while the GitHub CI lane on Python 3.12 successfully ran SciPy 1.18.1.

### Rule

- local compatible version may be used only for a non-authoritative canary;
- intended dependency must be verified in the target runtime;
- receipt records both Python and library version.

Same code across runtimes does not imply the same dependency contract.

---

## 20. Do not assume `mcporter` is globally installed or persistent

Later probes found:

```text
mcporter: not found
```

and a previously expected `node_modules/.bin/mcporter` path no longer existed.

For reproducible verifier use:

```text
package.json
package-lock.json
npm ci
./node_modules/.bin/mcporter ...
```

Pin the version and separate dependency installation from verifier execution.

---

## 21. On-demand `npx` is a bad verifier authority boundary

An on-demand Wolfram canary through `npx mcporter@0.9.0` timed out before verifier output; raw stdout was empty.

Accepted pattern:

```bash
npm ci
./node_modules/.bin/mcporter ...
```

This separates:

```text
dependency setup
        !=
verifier transport/execution
```

For simple capability discovery, a direct Streamable HTTP MCP handshake can be cheaper and cleaner:

```text
initialize
→ tools/list
```

---

## 22. Registry says public/no-auth != live endpoint is anonymous

Registry metadata described some endpoints as public/keyless, while direct anonymous MCP `initialize`/`tools/list` returned `401` for several of them. Other endpoints answered successfully in the same pass.

Represent separately:

```text
registry_metadata
live_handshake
observed_tool_inventory
auth_requirement
observed_at
```

Never collapse metadata into capability authority.

---

# Failure classification table

| Symptom | Likely failed layer | What it does **not** prove | First safe action |
|---|---|---|---|
| `sh: ... pipefail` | shell dialect | target logic broken | rerun explicitly under Bash |
| Markdown executed as shell | quoting/heredoc layer | intended document concept wrong | discard partial output; rewrite interpolation-free |
| `workspace_shell` timeout | execution window / long command | underlying remote job failed | split calls; re-read target |
| MarcoPolo `502` | connector/control plane | GitHub Action failed | query GitHub independently |
| GitHub write `403` | connector/app authority | repository read-only everywhere | use governed `gh-write`; native readback |
| `git push` `403` | smart-HTTP path | Git Database API cannot write | governed API fallback + exact readback |
| API ref read shows old SHA after write | stale read | write rolled back | fetch/query independently |
| `origin` missing | no checkout/local remote | remote branch absent | explicit repository URL |
| valid SHA rejected | shell validation | requested SHA invalid | Bash regex + test |
| receipt has launcher SHA | identity plumbing | wrong code necessarily executed | explicit experiment/launcher IDs |
| runner file missing later | artifact/runtime boundary | file never generated | inspect artifact/logs/runtime |
| `mcporter: not found` | dependency/path assumption | MCP endpoint unavailable | locked install or direct MCP probe |
| package cannot install | runtime compatibility | library unusable everywhere | verify in target runtime |
| worktree path missing | stale worktree metadata | branch safe to delete | inspect refs; then prune |
| registry says public, live `401` | metadata drift/access policy | endpoint nonexistent | preserve contradiction |

---

# Safe recipes

## Bash-safe MarcoPolo command

```bash
bash -lc 'set -euo pipefail
# bounded commands
'
```

## Pre-write Git state receipt

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin <branch>
git rev-parse origin/<branch>
```

## Post-write exact readback

```bash
git fetch origin <branch>
ACTUAL=$(git rev-parse origin/<branch>)
test "$ACTUAL" = "$EXPECTED_SHA"
```

Then run the relevant full test suite on that exact state.

## GitHub Actions experiment identity

```yaml
env:
  EXPERIMENT_SHA: ${{ inputs.experiment_sha }}
  LAUNCHER_SHA: ${{ github.sha }}
```

```bash
test "$(git rev-parse HEAD)" = "$EXPERIMENT_SHA"
```

## Bounded remote-job observation

Bad:

```text
workspace_shell: sleep several minutes → query GitHub → maybe timeout/502
```

Better:

```text
short query → return
short query → return
artifact/readback when complete
```

## Anonymous MCP capability probe

Preserve:

```text
endpoint URL
protocol version
initialize HTTP status
serverInfo
Mcp-Session-Id if present
tools/list HTTP status
exact tool names
raw response bytes/hash when promoted to evidence
observed_at
```

A successful `tools/list` proves only observed capability at that time; it is not authorization to use the server in Hermes/CI.

---

# Incident ledger

| Incident | What happened | Rule that came from it |
|---|---|---|
| Stage B launcher run `33701833762` | valid dispatch blocked by bad SHA shell guard | validate SHA with Bash regex |
| Stage B launcher run `33701986699` | pre-checkout `git ls-remote origin` failed | use explicit repository URL before checkout |
| Stage B resource run `33702091565` | execution succeeded, but receipt recorded launcher `GITHUB_SHA` as experiment commit; raw artifact upload also missing | explicit identities + artifact durability |
| Git Database publication episode | remote update succeeded but one immediate API read was stale | independent fetch/readback before correction |
| Git Database tree episode | published tree accidentally omitted an existing source file | full parent tree + exact-SHA test |
| Wolfram sidecar first transport | on-demand `npx mcporter` timed out with no verifier output | `package-lock` + `npm ci` |
| SciPy local canary | MarcoPolo Python 3.11 could not host SciPy 1.18.x | target-runtime compatibility is provenance |
| full-launcher worktree episode | branch metadata survived while worktree directory was gone | ref, registration, directory are separate state |
| Observatory issue creation | `/bin/sh` rejected `pipefail` before mutation | explicit Bash; distinguish pre-write failure |
| this README first write | nested `bash -lc` + heredoc broke and Markdown became shell input | avoid multi-layer heredoc quoting |
| GitHub workflow polling | MarcoPolo returned `502` while GitHub continued | connector failure != target failure |

---

# Epistemic rules for future agents

```text
search miss                  != absence
registry description         != live capability
HTTP/MCP success             != trust or authorization
connector timeout/502        != target failure
commit object exists         != repository tree is correct
workflow success             != durable evidence verified
GITHUB_SHA                   != checked-out experiment identity
local HEAD                   != remote branch authority
artifact name                != artifact bytes verified
same code                    != same runtime/dependency contract
```

When uncertain, preserve ambiguity and collect an independent observation rather than silently upgrading it to fact.

---

# Related workspace tools

- `../session-search/README.md` — reconstruct prior sessions and incident context.
- `../mcporter/README.md` — MCP client workbench; do not assume its runtime dependencies are globally installed.

Update this README whenever a new MarcoPolo failure mode produces a **reusable workaround or stronger verification rule**. One-off transient failures belong in session evidence; repeated or architecturally meaningful lessons belong here.

---

## 23. `gh auth setup-git` does not make a custom `GH_CONFIG_DIR` magically permanent

### Observed symptom

A governed push succeeded when invoked as:

```bash
GH_CONFIG_DIR=/workspace/.config/gh-write git push ...
```

but a later plain:

```bash
git fetch origin main
```

returned GitHub HTTP `403`.

### Root cause class

`gh auth setup-git` configures Git to use the GitHub CLI credential helper, but a custom MarcoPolo `GH_CONFIG_DIR` is process environment. A later Git process that invokes `gh` without that environment can resolve a different/no GitHub CLI credential context.

### Safe pattern

For governed Git operations in this workspace, bind the configuration explicitly for the command group:

```bash
export GH_CONFIG_DIR=/workspace/.config/gh-write
git fetch origin main
git push origin main
```

or prefix each command individually.

Do not interpret the resulting unauthenticated/wrong-context `403` as evidence that repository permissions changed until the same operation is retried in the intended governed credential context.

---

## 24. Google Drive session recovery has two authority boundaries: remote resolution and local materialization

### Observed symptoms

A real Barn Doctor recovery through the MarcoPolo Google Drive connection exposed several failure modes that can look like missing remote data when they are actually local/runtime issues:

- browsing a folder reported more rows than were rendered in the preview;
- using a display folder name as a provider parent path failed, while browsing the root exposed the stable folder ID;
- an exact remote filename resolved successfully, but a custom `--local-path` failed with local `Permission denied`;
- repeating the same download without a custom destination succeeded under `data/downloads`;
- the runtime had `unzip` but no `zip` executable;
- rebuilding Barn Doctor entries with Python `zipfile.write()` failed because source ZIP timestamps were earlier than 1980.

### Safe route

```text
connection list/test
        ↓
root browse
        ↓
resolve stable provider folder ID
        ↓
folder browse when discovery is needed
        ↓
exact-name connection download
        ↓
connection-managed data/downloads destination
        ↓
sha256 + unzip listing
        ↓
Session Search validation/import
```

Do not infer absence from a browse preview. Compare rendered preview length with `row_count`; when the exact filename is already known, prefer a direct bounded download attempt over recursively traversing Drive.

A download failure after remote resolution must be classified by layer:

```text
remote file resolved + local Permission denied
        = local destination failure
        != Drive file missing
```

### Archive handling

Do not install tools merely because a common CLI is missing. If a reviewed workflow must build a derived ZIP, the Python standard library is sufficient:

```python
import zipfile

with zipfile.ZipFile(output, "w", strict_timestamps=False) as zf:
    ...
```

Barn Doctor source archives remain immutable evidence. Any derived archive must carry a receipt containing at least source SHA-256, derived SHA-256, the selected session identity, excluded members, and the evidence rule used to justify selection.

### Search rule while diagnosing the route

Never fall back to broad recursive `grep -R /workspace`. Use `/workspace/tools/search/search.sh`, narrow paths and globs, and split large diagnostics into short independent calls. A timeout or control-plane block is an observer failure until the authoritative target is read separately.
