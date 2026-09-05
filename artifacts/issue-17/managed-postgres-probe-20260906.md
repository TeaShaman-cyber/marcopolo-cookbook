# Managed PostgreSQL memory probe — 2026-09-06

Status: `PARTIAL / BLOCKED_USER_SETUP`

## Observed

- A dedicated disposable Neon project was created on the free plan.
- PostgreSQL 17 compute is ready in `aws-us-east-2`.
- A direct provider-control query returned `sentinel = 1` from `neondb` as the synthetic probe owner.
- No connection string, password, token, or provider project identifier is recorded here.

## Boundary reached

MarcoPolo exposes PostgreSQL connection creation through its privileged browser setup flow. The CLI intentionally returns a setup URL rather than accepting plaintext credentials in the workspace.

Therefore the current classification is:

```text
PROVIDER_PROJECT_READY       = PASS
PROVIDER_READONLY_SENTINEL   = PASS
MARCOPOLO_PG_CONNECTION      = BLOCKED_USER_SETUP
REMOTE_WRITE                 = INCONCLUSIVE
EXACT_READBACK               = INCONCLUSIVE
IDEMPOTENT_RETRY             = INCONCLUSIVE
FRESH_INVOCATION_PERSISTENCE = INCONCLUSIVE
CROSS_CLIENT_PERSISTENCE     = UNKNOWN
```

This is a useful security observation: completing the governed connection requires the operator to transfer the database credential directly between provider and MarcoPolo setup surfaces, keeping secret material outside model context and `/workspace`.

## Next executable step

After the pg connection appears in `connection list`, run a MarcoPolo `SELECT 1` sentinel, then create the synthetic probe table, insert one canary with caller-stable `operation_id`, exact-read it, retry the same operation, and verify exactly one logical row.
