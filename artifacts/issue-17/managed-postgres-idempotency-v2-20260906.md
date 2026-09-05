# Managed PostgreSQL idempotency probe v2 — 2026-09-06

Status: `PASS / RECEIPT_REPLAY_AND_MISMATCH_GUARD_VERIFIED`

This is a follow-up correction probe for PR #20 after Codex review of the first managed-PostgreSQL receipt semantics.

The earlier probe proved exactly-one logical-row behavior but used `inserted=true/false` in the response, which was insufficient to prove replay of the original logical receipt after a lost acknowledgement. This v2 probe keeps the old evidence immutable and verifies the stronger contract separately.

## Contract under test

```text
canonical request bytes
      ↓
request_fingerprint = sha256(...)
      ↓
operation_id + request_fingerprint
      ↓
durable event + immutable stored receipt
```

Retry semantics:

```text
same operation_id + same request_fingerprint
  -> return same stored receipt
  -> attempt-local inserted flag may differ

same operation_id + different request_fingerprint
  -> IDEMPOTENCY_KEY_REUSE_MISMATCH
  -> no receipt replay as successful acceptance
  -> no new logical row
```

## Observed results

First retain through MarcoPolo:

```text
status            = OK
attempt_inserted  = true
operation_id      = op-neon-marcopolo-v2-20260906-001
request_fingerprint = b89b41aa1c7160a1721ce7595f8d015c2abdb40fb9e7affbb4136ae17980942a
```

Identical retry through a separate MarcoPolo query invocation:

```text
status            = OK
attempt_inserted  = false
same_receipt      = true
same_committed_at = true
```

Same `operation_id` with different canonical event bytes:

```text
status             = IDEMPOTENCY_KEY_REUSE_MISMATCH
incoming_fingerprint != stored_fingerprint
replayed_receipt   = null
attempt_inserted   = false
```

Final authoritative row count:

```text
logical_rows = 1
```

A separate Neon provider-side readback, outside the MarcoPolo query route, returned the same stored fingerprint, event ID, committed receipt, and `logical_rows = 1`.

## Result matrix

```text
IMMUTABLE_RECEIPT_STORED          = PASS
IDENTICAL_RETRY_SAME_RECEIPT      = PASS
IDENTICAL_RETRY_SAME_COMMITTED_AT = PASS
ATTEMPT_DIAGNOSTIC_SEPARATE       = PASS
SAME_KEY_DIFFERENT_BYTES_REJECT   = PASS
MISMATCH_REPLAYS_RECEIPT          = NO
LOGICAL_ROW_COUNT_AFTER_MISMATCH  = 1
DISTINCT_CLIENT_READBACK          = PASS
REAL_LOST_ACK_INJECTION           = NOT_TESTED
```

`REAL_LOST_ACK_INJECTION = NOT_TESTED` remains explicit: the probe verifies that a later retry can recover the original stored receipt, but it does not inject an actual network/transport acknowledgement loss after server commit.

## MarcoPolo run receipts

```text
create v2 table    run_20260905_232307_1162e395
first retain       run_20260905_232308_5abb0c63
identical retry    run_20260905_232309_3b6661be
mismatch check     run_20260905_232416_5a042c97
final count        run_20260905_232418_751d2f07
```

## Portable-core follow-up

The same review cycle also introduced executable `memory-core-v0.1` conformance fixtures:

```text
tests/fixtures/memory-core-v0.1.json
tests/test_memory_core_fixture.py
```

They pin the lifecycle vocabulary, exact scope/filter behavior, deterministic tie-break ordering, cursor encoding, and page continuation outcomes. Future adapters must reproduce these fixture outcomes before richer retrieval semantics are compared.

---

Prepared collaboratively by Semyon Poklad and Шут (Jester), ChatGPT / GPT-5.6 Sol.
