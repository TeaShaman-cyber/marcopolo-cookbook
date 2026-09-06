WITH incoming AS (
    SELECT
        convert_from(decode('{{ operation_id_hex }}', 'hex'), 'UTF8') AS operation_id,
        convert_from(decode('{{ request_fingerprint_hex }}', 'hex'), 'UTF8') AS request_fingerprint,
        convert_from(decode('{{ event_id_hex }}', 'hex'), 'UTF8') AS event_id,
        convert_from(decode('{{ scope_hex }}', 'hex'), 'UTF8') AS scope,
        convert_from(decode('{{ source_class_hex }}', 'hex'), 'UTF8') AS source_class,
        convert_from(decode('{{ lifecycle_state_hex }}', 'hex'), 'UTF8') AS lifecycle_state,
        convert_from(decode('{{ created_at_hex }}', 'hex'), 'UTF8')::timestamptz AS created_at,
        convert_from(decode('{{ provenance_json_hex }}', 'hex'), 'UTF8')::jsonb AS provenance,
        convert_from(decode('{{ payload_json_hex }}', 'hex'), 'UTF8')::jsonb AS payload
), candidate AS (
    SELECT incoming.*, clock_timestamp() AS committed_at
    FROM incoming
), ins AS (
    INSERT INTO public.theseus_memory_events_v01(
        operation_id,
        request_fingerprint,
        event_id,
        scope,
        source_class,
        lifecycle_state,
        created_at,
        provenance,
        payload,
        committed_at,
        receipt
    )
    SELECT
        operation_id,
        request_fingerprint,
        event_id,
        scope,
        source_class,
        lifecycle_state,
        created_at,
        provenance,
        payload,
        committed_at,
        jsonb_build_object(
            'receipt_version', 'memory-receipt-v0.1',
            'operation_id', operation_id,
            'request_fingerprint', request_fingerprint,
            'event_id', event_id,
            'committed_at', committed_at,
            'commit_state', 'DURABLY_COMMITTED'
        )
    FROM candidate
    ON CONFLICT (operation_id) DO NOTHING
    RETURNING *
)
SELECT
    'OK'::text AS status,
    true AS attempt_inserted,
    operation_id,
    request_fingerprint,
    event_id,
    committed_at,
    receipt::text AS stored_receipt_json
FROM ins
UNION ALL
SELECT
    CASE
        WHEN stored.request_fingerprint = incoming.request_fingerprint THEN 'OK'
        ELSE 'IDEMPOTENCY_KEY_REUSE_MISMATCH'
    END AS status,
    false AS attempt_inserted,
    stored.operation_id,
    stored.request_fingerprint,
    stored.event_id,
    stored.committed_at,
    CASE
        WHEN stored.request_fingerprint = incoming.request_fingerprint THEN stored.receipt::text
        ELSE NULL
    END AS stored_receipt_json
FROM public.theseus_memory_events_v01 AS stored
CROSS JOIN incoming
WHERE stored.operation_id = incoming.operation_id
  AND NOT EXISTS (SELECT 1 FROM ins);
