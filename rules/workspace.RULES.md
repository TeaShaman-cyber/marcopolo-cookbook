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

Canonical route:

```bash
/workspace/tools/session-search/search.sh 'query terms'
```

If a relevant session title or `session_id` is known, prefer session-scoped
retrieval.

Session Search is historical interaction evidence. It is not semantic memory
and it is not authority for current runtime state, permissions, or tool
capabilities.

A search miss means `UNKNOWN`, not proof of absence, especially for a
`PARTIAL_SESSION_SLICE` or otherwise incomplete corpus.

If Session Search is unavailable or its corpus verification fails, state that
explicitly. Do not silently present remembered, reconstructed, or other
retrieved context as if it came from Session Search.

## Shell dialect

`workspace_shell` command strings may execute through `/bin/sh`, not Bash.
Use plain POSIX-compatible shell for simple commands. When a command depends on
Bash semantics such as `pipefail`, `[[ ... ]]`, arrays, process substitution,
or a Bash script, invoke Bash explicitly with `bash -lc '<command>'` or `bash script.sh`.

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
failure procedures remain in `marcopolo/README.md`.

## GitHub operational route

When GitHub work is performed through MarcoPolo, use the workspace GitHub
profiles rather than guessing from whichever client connector happens to be
available.

For reads through MarcoPolo:

```bash
GH_CONFIG_DIR=/workspace/.config/gh gh ...
```

The native ChatGPT GitHub plugin is also an allowed lightweight read route for
bounded current-state inspection when only the answer or check is needed and no
durable copy, bulk extraction, or workspace-local processing is required. A
plugin read is evidence for the state returned by that route; it does not create
write authority or workspace persistence.

For explicitly authorized writes through MarcoPolo:

```bash
GH_CONFIG_DIR=/workspace/.config/gh-write gh ...
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

Git-backed writes may use `git` under the same `gh-write` environment. After
any mutation, verify the exact remote postcondition. Do not infer write
capability from read authentication, and do not silently substitute a different
GitHub route after an authentication failure without reporting the route change.
