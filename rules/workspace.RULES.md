<!--
Canonical source: TeaShaman-cyber/marcopolo-cookbook/rules/workspace.RULES.md
Runtime projection target: /workspace/RULES.md

This file is version-controlled Git state. Human acceptance and Git promotion
remain separate from runtime materialization. The runtime copy is a projection,
not an independent authority. After materializing it, verify content equality/hash.
-->

# MarcoPolo Workspace Rules

## Session continuity / Session Search

When a task materially depends on prior chats, branches, previous decisions,
or asks to restore or continue earlier work, consult Session Search before
answering from reconstructed context alone.

Canonical interactive route:

```bash
/workspace/tools/session-search/search.sh 'query terms'
```

The search wrapper owns corpus selection and performs a cheap **local freshness
preflight** before invoking Session Search. That preflight establishes only that
the runtime helper projection matches the local cookbook source, the bound
Session Search implementation is present, its `session_search` tree is Git-clean,
any configured local HEAD/ref pin matches, and the explicitly bound corpus is
available with an observable generation token. After that preflight, normal search
may use a freshness-bound disposable local read projection for performance. That
cache is never authority: if refresh/validation fails, search reports a degraded
route on stderr and falls back to the explicitly bound durable corpus. It performs
no network access and no full corpus integrity/rebuild verification.

For explicit local diagnostics, use:

```bash
/workspace/tools/session-search/status.sh --json
```

`READY` means **local route coherence**, not remote freshness and not full
corpus integrity. When remote freshness of the bound implementation matters, use
the existing repository-currentness route described below rather than teaching
Session Search a second currentness mechanism. If status reports `STALE`,
`BLOCKED`, or `UNKNOWN` for a property required by the task, do not silently
treat remembered state, an arbitrary checkout, or filesystem discovery as
equivalent evidence.

Use the heavy acceptance path only when durable-corpus integrity, import health,
or rebuild equivalence is actually in question. Acceptance does not use the
interactive local cache:

```bash
/workspace/tools/session-search/acceptance.sh
```

Do not put full acceptance/rebuild on the ordinary interactive search path. Do
not recursively traverse `/workspace` to rediscover Session Search state; use
the bounded status/search routes above.

If a relevant session title or `session_id` is known, prefer session-scoped
retrieval. Session Search is historical interaction evidence. It is not semantic
memory and it is not authority for current runtime state, permissions, or tool
capabilities.

A search miss means `UNKNOWN`, not proof of absence, especially for a
`PARTIAL_SESSION_SLICE` or otherwise incomplete corpus. If Session Search is
unavailable or its required freshness/integrity evidence cannot be established,
state that explicitly.

## Repository currentness / canonical checkout

A visible repository path and a clean working tree do not prove that the
checked-out branch is the current authoritative source. Before using workspace
repository files as canonical operational guidance, establish the authoritative
ref for the task and refresh that ref when freshness materially matters.

For the canonical MarcoPolo cookbook, the normal currentness check is:

```bash
git -C /workspace/marcopolo-cookbook fetch origin main
/workspace/marcopolo-cookbook/git-worktree-currentness.sh /workspace/marcopolo-cookbook origin/main
```

`VERIFIED` means the worktree HEAD equals the selected authoritative ref and the
worktree has no local modifications. `BLOCKED` or `UNKNOWN` means the worktree
must not be silently treated as current canonical state.

Do not destroy, reset, or switch a dirty or active feature/research worktree
merely to obtain canonical guidance. Prefer reading the authoritative ref
directly (for example `git show origin/main:<path>`) or use a separate clean
worktree.

Do not infer that an existing non-main branch, checkout, or worktree is active
user-authored work merely because it exists in `/workspace`. Treat its
provenance and ownership as `UNKNOWN` until current issue/PR/session evidence or
an explicit user statement establishes otherwise. Identify its repository,
branch/HEAD, dirty state, and linked issue/PR before deciding to continue,
retire, or preserve it. Prefer disposable worktrees or short-lived branches for
bounded agent changes, and remove them after verified merge when no recovery
intent remains; do not accumulate new long-lived workspace branches by default.

A runtime projection such as `/workspace/RULES.md` remains distinct from both
the current Git ref and any stale workspace checkout; verify the relevant
postcondition explicitly.

## QA / verifier discovery

Before authoring bespoke verification for repository or runtime work in
MarcoPolo, inspect project-native check/acceptance entrypoints and the current
runtime QA/tool inventory first. Prefer the thinnest existing deterministic
verifier whose scope directly establishes the claim.

Use repository-local check scripts, acceptance runners, linters, validators,
analyzers, and runtime inventories before reimplementing their semantics. Do
not install or require a heavier tool merely because it exists when an
available narrower route is sufficient.
If a repository provides `tools/dev/check`, use it as the first pre-review QA
gate before composing bespoke checks. Add shared generic mechanical pre-review
checks to `tools/dev/check` instead of scattering ad-hoc check scripts; use a
separate helper only for a genuinely different scoped workflow. If unavailable
or inapplicable, continue discovery and do not treat that as PASS.

If no available verifier covers the claim, add a bespoke check only for the
observed gap. An unavailable, unrun, or uncovered verification path is UNKNOWN,
never PASS. Tool availability or capability does not grant authority or
permission.

## Shell dialect

`workspace_shell` command strings may execute through `/bin/sh`, not Bash.
Use plain POSIX-compatible shell for simple commands. When a command depends on
Bash semantics such as `pipefail`, `[[ ... ]]`, arrays, process substitution,
or a Bash script, invoke Bash explicitly. For quoting-sensitive or multiline
commands, prefer a Bash script or deterministic payload over nesting an
arbitrary command inside another shell quoting layer.

A shell-dialect error that occurs before target logic runs is a pre-execution
failure, not evidence that the intended mutation failed or partially succeeded.
Verify the target postcondition before retrying.

The MarcoPolo control plane may also reject a workspace_shell payload before
execution when the request contains a literal parent-path sequence formed by
two dots followed immediately by a slash. Treat that as a pre-execution
transport/filter failure, not evidence about the target mutation. When the path
is legitimate, construct or encode it inside the shell/runtime so that sequence
is not present in the outer request payload, then verify the target postcondition.

Detailed quoting, heredoc, deterministic payload transport, and connector
failure procedures remain in `/workspace/marcopolo-cookbook/marcopolo/README.md`.

## GitHub operational route

When GitHub work is performed through MarcoPolo, use the workspace GitHub
profiles rather than guessing from whichever client connector happens to be
available.


### GitHub capability routing

Choose the GitHub route by the provider capability required, not only by whether
the operation is nominally a read or a write.

Prefer the workspace-owned verified CLI when present:

```bash
GH_BIN=/workspace/.local/bin/gh
[ -x "$GH_BIN" ] || GH_BIN=/usr/local/bin/gh
```

Use this matrix:

| Operation | Normal route | Required proof |
|---|---|---|
| bounded repo/issue/PR read | native GitHub plugin, or `GH_CONFIG_DIR=/workspace/.config/gh` for workspace-local processing | smallest live read succeeds |
| Projects V2 read | capability-verified Projects profile; currently `GH_CONFIG_DIR=/workspace/.config/gh-write` | `auth status` plus live Project probe succeeds |
| explicitly authorized GitHub mutation | `GH_CONFIG_DIR=/workspace/.config/gh-write` | mutation plus exact remote readback |
| authorized Projects V2 mutation | `gh-write` with verified Projects capability | Project mutation plus Project readback |
| ordinary Git smart-HTTP | cookbook-managed credential helper pinned to `gh-write` | helper check; remote readback when freshness matters |

The default MarcoPolo profile may use a GitHub App user token (`ghu_...`).
Repository reads succeeding through that token do not prove Projects access.
GitHub App user tokens do not expose classic OAuth scopes like a CLI OAuth
token (`gho_...`), so an empty `X-OAuth-Scopes` header is not proof of no
permissions. Likewise, human-account `admin` or `push` rights do not establish
integration-token authority.

Projects V2 is therefore a capability-specific exception to the simple
read/write split. Verify it directly:

```bash
GH_CONFIG_DIR=/workspace/.config/gh-write "$GH_BIN" auth status -h github.com
GH_CONFIG_DIR=/workspace/.config/gh-write "$GH_BIN" project list --owner TeaShaman-cyber --format json
```

Only treat Projects access as available after the live Project probe succeeds.
A response with a positive `totalCount` but null Project nodes is a degraded
authorization/capability signal, not evidence that the Projects do not exist.
Do not use the default profile for a Project read merely because the operation
is read-only.

For reads through MarcoPolo:

```bash
GH_CONFIG_DIR=/workspace/.config/gh "$GH_BIN" ...
```

The native ChatGPT GitHub plugin is also an allowed lightweight read route for
bounded current-state inspection when only the answer or check is needed and no
durable copy, bulk extraction, or workspace-local processing is required. A
plugin read is evidence for the state returned by that route; it does not create
write authority or workspace persistence.

For explicitly authorized writes through MarcoPolo:

```bash
GH_CONFIG_DIR=/workspace/.config/gh-write "$GH_BIN" ...
```

MarcoPolo remains the default GitHub write route when it is suitable. The native
ChatGPT GitHub plugin may be used as an explicit write fallback when MarcoPolo is
materially obstructed by transport, quoting, or request-filter mechanics, or
when working around those mechanics would add avoidable mutation risk or
complexity. Native-plugin write capability is not permission and must not become
the default merely because it is available.

Before a native-plugin fallback write, current user intent must already authorize
the mutation. Make the route change visible, perform the smallest sufficient
mutation, and verify the exact remote postcondition through an independently
available read when practical.

For ordinary Git operations against `github.com`, install the cookbook-managed
credential binding once per workspace/runtime configuration:

```bash
/workspace/marcopolo-cookbook/github-git-auth.sh --install
```

After that, plain `git fetch`, `git pull`, and explicitly authorized `git push`
use the `gh-write` credential helper without requiring `GH_CONFIG_DIR` in every
shell command. `gh` commands still use the explicit read/write profiles shown
above; the Git helper changes credential selection only and does not grant
mutation permission.

Verify the binding with:

```bash
/workspace/marcopolo-cookbook/github-git-auth.sh --check
```

After any Git mutation, verify the exact remote postcondition. Do not infer
write permission from credential availability, and do not silently substitute a
different GitHub route after an authentication failure without reporting the
route change.
