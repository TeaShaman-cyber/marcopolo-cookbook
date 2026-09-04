# OpenAI GitHub connector instability — sanitized longitudinal evidence

Status: `OBSERVED / REPRODUCIBLE ACROSS MULTIPLE SESSIONS / ROOT CAUSE UNKNOWN`

This note is a public, sanitized evidence packet for upstream reporting. It deliberately excludes tokens, GitHub App installation IDs, private repository names, private conversation text, and raw authenticated payloads.

## Summary

The observed failure is not one stable permission error. Connector authority can become visible and useful, then disappear during the same authenticated workflow.

```mermaid
flowchart LR
  A[Reconnect / reinstall] --> B[Identity visible]
  B --> C[Repo permission read: admin]
  C --> D{Later operation}
  D -->|source search| E[connector unavailable]
  D -->|first harmless write| E
  D -->|readback| E
  E --> F[separate governed GitHub route still reads/writes target]
```

## FACT

- Historical baseline: native connector reads worked while writes returned `403 Resource not accessible by integration`.
- After a full revoke/reinstall/reconnect with broad repository authorization, authenticated identity and `admin` collaborator permission were visible through the native connector.
- In the same working period, a first harmless write path, a source-search path, and later an independent readback caused the native connector to become unavailable/disabled rather than consistently returning the prior 403 class.
- A separately authenticated GitHub CLI route remained able to observe or mutate the same user-owned repository state during these native-connector failures.
- Reauthorization therefore changed the visible capability state but did not make the native connector stable.

## INFERENCE

The failure is consistent with connector/session authority or tool-registry state becoming invalid after successful initialization. This is stronger than a static “GitHub App lacks permission” explanation because the connector first demonstrates authenticated identity and repository authority, then loses the tool path while the underlying GitHub account/repository remains accessible through a control route.

## UNKNOWN

- GitHub App installation/cache propagation vs MCP/tool discovery/runtime invalidation.
- Whether a particular GitHub operation triggers the state loss or merely encounters it first.
- Whether connector state is scoped to a chat, branch/thread lineage, runtime worker, or account session.

## Impact

This makes the connector unsuitable as the sole authority path for engineering workflows that require `write -> independent readback`. A failed/disappeared readback cannot safely be interpreted as write failure, so every consequential workflow needs a second GitHub route and reconciliation logic.

## Related upstream reports

- `openai/codex#37330` — reconnect succeeds, repositories/write authority still fail.
- `openai/codex#39018` — selective read endpoints return 403.
- `openai/codex#40729` — connector loses tools after permission changes.

This packet adds longitudinal state-transition evidence: **authority visible -> later tool loss in the same authenticated working period**.

Machine-readable companion: `2026-09-04-openai-github-connector-instability.json`.
