# Managed PostgreSQL memory probe — 2026-09-06

Status: `PASS / REMOTE_CORE_PATH_VERIFIED`

## Scope

This receipt covers only a synthetic managed-PostgreSQL storage probe for issue #17. It does **not** claim that the full Skill-directed memory loop, host-level lifecycle hooks, fresh-chat attribution, or richer recall semantics are verified.

No connection string, password, token, or provider project identifier is recorded here.

## Observed path

```text
operator enters Neon credential in MarcoPolo browser setup
        ↓
MarcoPolo governed pg connection
        ↓
Neon PostgreSQL 17
        ↓
synthetic create / retain / readback / retry
        ↓
independent provider-side readback
```

Observed facts:

- A dedicated disposable Neon project exists on the free plan.
- PostgreSQL 17 compute is reachable in `aws-us-east-2`.
- A direct provider-control sentinel returned `1` from `neondb` as the synthetic probe owner.
- MarcoPolo saved a `pg` connection with `query`, `test`, and `describe` capabilities.
- `connection test` succeeded through MarcoPolo.
- A governed MarcoPolo identity query reached the same `neondb` / synthetic owner and reported PostgreSQL 17.11.
- A synthetic probe table was created remotely through MarcoPolo.
- The first retain for caller-stable `operation_id = op-neon-marcopolo-20260906-001` returned `inserted=true`.
- A separate retry with the same operation id returned the same logical event with the same `created_at` and `inserted=false`.
- A fresh MarcoPolo query read the exact event back.
- A separate count query reported exactly one logical row for that operation id.
- An independent Neon provider client, outside the MarcoPolo query path, read back the same event and also reported one logical row.
- Two concurrent MarcoPolo retain calls raced on a second shared `operation_id`; one returned `inserted=true`, the other `inserted=false`, and the final count remained exactly one logical row.

Synthetic canary:

```text
SONAR-MEMORY-PROBE-0906-NEON-4821
```

## Result matrix

```text
PROVIDER_PROJECT_READY          = PASS
PROVIDER_READONLY_SENTINEL      = PASS
MARCOPOLO_PG_CONNECTION         = PASS
MARCOPOLO_CONNECTION_SENTINEL   = PASS
REMOTE_WRITE                    = PASS
EXACT_READBACK                  = PASS
IDEMPOTENT_RETRY                = PASS
CONCURRENT_SAME_KEY_RACE        = PASS
FRESH_QUERY_INVOCATION_READBACK = PASS
DISTINCT_CLIENT_READBACK        = PASS
LOGICAL_ROW_COUNT_AFTER_RETRY   = 1
LOST_ACKNOWLEDGEMENT_INJECTION  = NOT_TESTED
FRESH_CHAT_RECALL               = NOT_TESTED
CROSS_EXECUTOR_PERSISTENCE      = UNKNOWN
```

`DISTINCT_CLIENT_READBACK = PASS` means an acknowledged write performed through the MarcoPolo pg route was independently visible through the Neon provider control surface. It does not prove executor replacement, worker replacement, or a fresh ChatGPT session.

For this remote authoritative-store lane, MarcoPolo local NFS/file-lock behavior is not on the canonical PostgreSQL durability path. Local filesystem safety still matters for any cache, query artifact, JSONL receipt, SQLite/Holographic projection, or DuckDB projection kept under `/workspace`.

## Idempotency evidence

The probe used a primary key on `operation_id` and an `INSERT ... ON CONFLICT DO NOTHING` retain query that always returns the logical event. The first invocation reported:

```text
inserted = true
created_at = 2026-09-05T23:10:20.581Z
```

The retry reported:

```text
inserted = false
created_at = 2026-09-05T23:10:20.581Z
```

The subsequent count was:

```text
logical_rows = 1
```

This verifies deterministic retry behavior for a normal repeated acknowledgement path. A separate concurrent same-key race also verified exactly-one logical-row behavior across two overlapping governed writes. It does **not** yet simulate a real lost acknowledgement after server commit.

## MarcoPolo run receipts

```text
identity query     run_20260905_230958_802b6848
create table       run_20260905_231018_ae75530a
retain first       run_20260905_231020_69f9833a
retain retry       run_20260905_231033_976c4b14
exact readback     run_20260905_231034_59a83ab6
uniqueness count   run_20260905_231036_c44e3d92
race writer A      run_20260905_231151_ff12977e
race writer B      run_20260905_231151_f13dd06a
race final count   run_20260905_231154_a7ae19e3
```

These run IDs are operational evidence references only; they do not contain credential material in this receipt.

## Security boundary observation

The database credential was transferred by the operator directly from the provider UI into the MarcoPolo privileged browser setup. The model-visible workflow did not request or record the password or connection string. This is consistent with the intended privileged connection boundary.

## Next falsification steps

1. inject or emulate acknowledgement loss after remote commit if a controllable boundary becomes available;
2. run an adapter-only canary with adapter-enabled and adapter-disabled controls;
3. preserve `CROSS_EXECUTOR_PERSISTENCE = UNKNOWN` until a genuinely distinct executor/session boundary is observed;
4. keep embedded-file backends as separate comparison/projection lanes rather than inferring their safety from this remote PostgreSQL result.
