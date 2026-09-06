WITH params AS (
    SELECT
        convert_from(decode('{{ scope_hex }}', 'hex'), 'UTF8') AS scope,
        convert_from(decode('{{ event_id_hex }}', 'hex'), 'UTF8') AS event_id
), target AS (
    SELECT e.*
    FROM public.theseus_memory_events_v01 AS e
    CROSS JOIN params AS p
    WHERE e.scope = p.scope
      AND e.event_id = p.event_id
    LIMIT 1
)
SELECT
    CASE WHEN EXISTS (SELECT 1 FROM target) THEN 'HIT' ELSE 'MISS_UNKNOWN' END AS status,
    (
        SELECT jsonb_build_object(
            'event_id', event_id,
            'operation_id', operation_id,
            'scope', scope,
            'source_class', source_class,
            'lifecycle_state', lifecycle_state,
            'created_at', to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
            'provenance', provenance,
            'payload', payload
        )::text
        FROM target
    ) AS stored_event_json;
