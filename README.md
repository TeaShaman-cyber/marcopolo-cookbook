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
- [mcporter workbench](mcporter/README.md) — bounded MCP client setup, inventory, probes, and acceptance checks.
- [Search helpers](search/README.md) — lightweight search tooling used in the workspace.
- [Jester forum notes](jester-forum/README.md) — bounded forum workflow notes.

Additional top-level scripts provide GitHub/wiki wrappers and access checks used by the workspace.

## Security rule

Secrets, tokens, cookies, auth caches, `.env` files, private keys, and generated credential dumps are never committed. Authentication-related scripts are eligible only when they contain reusable logic and symbolic references to credential sources rather than credential values.

## Repository hygiene

Generated dependencies and caches such as `node_modules/`, `__pycache__/`, Python bytecode, virtual environments, logs, and unreviewed `mcporter/traces/` are excluded from version control.

## Updating the cookbook

Reusable failure modes and verified workarounds belong in the cookbook. One-off transient incidents remain session evidence until they yield a general operational rule.

## Cloud reference

See `cloud-reference/` for passive hosting evidence, reviewed MCP documentation wrappers, and connector-filter diagnostics.
