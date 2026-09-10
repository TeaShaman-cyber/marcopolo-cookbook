# MarcoPolo Cookbook

Practical recipes, runbooks, and small tools distilled from real MarcoPolo workspace operations in Theseus research.

The repository favors reproducible operational patterns over hypothetical examples. Credentials may be referenced by interface or environment-variable name, but credential values do not belong in this repository.

## Runtime boundaries

Three execution environments must be treated as distinct:

```text
ChatGPT conversation runtime (/mnt/data)
        !=
MarcoPolo workspace (/workspace)
        !=
GitHub Actions runner
```

A path, dependency, or artifact observed in one runtime is not assumed to exist in another.

## Components

- [MarcoPolo field notes](marcopolo/README.md) — shell, connector, Git/GitHub, worktree, artifact, runtime, and MCP failure modes with verified workarounds.
- [Session Search](session-search/README.md) — reconstruct prior session evidence from exported conversation history.
- [Workspace RULES projection](rules/workspace.RULES.md) — Git-reviewed source for small workspace-wide runtime routing guidance.
- [`github-git-auth.sh`](github-git-auth.sh) — one-time/default GitHub Git credential binding to the governed `gh-write` profile.
- [Project IaC](project/README.md) — Git-versioned source for cross-chat project routing, authority, and change-control policy.
- [mcporter workbench](mcporter/README.md) — bounded MCP client setup, inventory, probes, and acceptance checks.
- [MCPJam CLI workbench](mcpjam-cli/README.md) — independent MCP transport/protocol diagnostics, probes, and Agent Skills inspection.
- [Search helpers](search/README.md) — lightweight search tooling used in the workspace.
- [Jester forum notes](jester-forum/README.md) — bounded forum workflow notes.

Additional top-level scripts provide GitHub/wiki wrappers and access checks used by the workspace.

## Small review methods

- [Feynman checkpoint](docs/methods/feynman-checkpoint.md) — before design/review work, explain the mechanism simply and remove complexity that the task does not require.
- [Five Whys](docs/methods/five-whys.md) — after an observed failure, trace evidence-backed causes to the smallest responsible layer and verify the postcondition.

Keep these methods small and separate. They are reusable operational policies, not a new reasoning framework; future context routing may include them without duplicating their prose.

## Security rule

Secrets, tokens, cookies, auth caches, `.env` files, private keys, and generated credential dumps are never committed. Authentication-related scripts are eligible only when they contain reusable logic and symbolic references to credential sources rather than credential values.

## Repository hygiene

Generated dependencies and caches such as `node_modules/`, `__pycache__/`, Python bytecode, virtual environments, logs, and unreviewed `mcporter/traces/` are excluded from version control.

## Updating the cookbook

Reusable failure modes and verified workarounds belong in the cookbook. One-off transient incidents remain session evidence until they yield a general operational rule.

## Cloud reference

See `cloud-reference/` for passive hosting evidence, reviewed MCP documentation wrappers, and connector-filter diagnostics.
