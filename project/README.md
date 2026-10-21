# Project IaC

This directory stores the Git-versioned source for cross-chat project operating policy.

## Authority and projection

```text
accepted Git source
  -> project/project-contract.wl
  -> ChatGPT Project Settings projection
  -> PROJECT_CONTRACT_PROBE runtime check
```

A merge proves only the accepted Git source. It does not prove that ChatGPT Project Settings were updated.

For revision `2026-10-skill-router-v9`, a correctly updated project runtime must answer:

```text
PROJECT_CONTRACT_PROBE
-> PC_OK_V9
```

## Layering

- Project Contract: cross-chat authority/permission, change control, and thin routing invariants.
- `marcopolo-core-router`: recurring MarcoPolo/GitHub operational routing guardrails.
- Workspace RULES: MarcoPolo runtime invariants and route mechanics.
- Cookbook: detailed procedures, recovery, historical evidence, and tool-specific failures.

The v7 Git bootstrap and its rationale are tracked in GitHub Issue #31. The v8 routine project-owned promotion rule is tracked in GitHub Issue #108. The v9 skill-router reduction is tracked in GitHub Issue #114.
