# Adapter-only canary — 2026-09-06

Implementation under test: `d4ceec9cac8095d404841127699e27aad38b0b5b`.

## Result

```text
bootstrap                    PASS
retain                       PASS
exact readback               PASS
recall                       PASS
reconcile                    PASS
adapter-disabled control     PASS
independent Neon readback    PASS

model-mediated Skill path    NOT_TESTED
fresh-session recall         NOT_TESTED
```

The canary value was generated randomly inside the MarcoPolo runtime. The durable receipt stores only its SHA-256, not the raw value. Recall compared the backend-returned payload to the runtime-only value before reporting PASS.

The adapter call trace was:

```text
bootstrap -> retain -> readback -> recall -> reconcile
```

The disabled-control recall raised `ADAPTER_DISABLED` before the runner and did not add a trace entry.

Independent provider-side readback confirmed the same synthetic `event_id` / `operation_id`, `OBSERVED` lifecycle state, synthetic payload kind, and `DURABLY_COMMITTED` receipt state.

## Boundaries

This proves the direct adapter path over the governed MarcoPolo PostgreSQL connection. It does **not** yet prove Skill selection, model-mediated invocation, or fresh-session automatic recall.

One initial harness attempt failed on `/tmp` Python import path resolution before any database call. The successful run used an explicit worktree `PYTHONPATH`; no database mutation occurred in the failed attempt.

No connection string, credential, provider project identifier, live connection name, or raw canary value is stored in this receipt.
