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

## GitHub operational route

When GitHub work is performed through MarcoPolo, use the workspace GitHub
profiles rather than guessing from whichever client connector happens to be
available.

For reads:

```bash
GH_CONFIG_DIR=/workspace/.config/gh gh ...
```

For explicitly authorized writes:

```bash
GH_CONFIG_DIR=/workspace/.config/gh-write gh ...
```

Git-backed writes may use `git` under the same `gh-write` environment. After
any mutation, verify the exact remote postcondition. Do not infer write
capability from read authentication, and do not silently substitute a different
GitHub route after an authentication failure without reporting the route change.
