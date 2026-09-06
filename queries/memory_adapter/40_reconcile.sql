WITH params AS (
    SELECT convert_from(decode('{{ scope_hex }}', 'hex'), 'UTF8') AS scope
), authorized_events AS (
    SELECT event_id
    FROM public.theseus_memory_events_v01 AS e
    CROSS JOIN params AS p
    WHERE e.scope = p.scope
), integrity_bad AS (
    SELECT 1
    FROM public.theseus_memory_relations_v01 AS r
    LEFT JOIN public.theseus_memory_events_v01 AS a
        ON a.event_id = r.endpoint_a_event_id
    LEFT JOIN public.theseus_memory_events_v01 AS b
        ON b.event_id = r.endpoint_b_event_id
    CROSS JOIN params AS p
    WHERE (
        r.endpoint_a_event_id IN (SELECT event_id FROM authorized_events)
        OR r.endpoint_b_event_id IN (SELECT event_id FROM authorized_events)
    )
      AND (
          a.event_id IS NULL
          OR b.event_id IS NULL
          OR r.scope <> p.scope
          OR a.scope <> p.scope
          OR b.scope <> p.scope
      )
    LIMIT 1
), safe_relations AS (
    SELECT r.*
    FROM public.theseus_memory_relations_v01 AS r
    JOIN public.theseus_memory_events_v01 AS a
        ON a.event_id = r.endpoint_a_event_id
    JOIN public.theseus_memory_events_v01 AS b
        ON b.event_id = r.endpoint_b_event_id
    CROSS JOIN params AS p
    WHERE r.scope = p.scope
      AND a.scope = p.scope
      AND b.scope = p.scope
)
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM integrity_bad) THEN 'INTEGRITY_SCOPE_VIOLATION'
        ELSE 'OK'
    END AS status,
    CASE
        WHEN EXISTS (SELECT 1 FROM integrity_bad) THEN NULL
        ELSE jsonb_build_object(
            'status', 'OK',
            'duplicates', '[]'::jsonb,
            'conflicts', COALESCE((
                SELECT jsonb_agg(relation_id ORDER BY relation_id)
                FROM safe_relations WHERE relation_kind = 'CONFLICT'
            ), '[]'::jsonb),
            'supersession', COALESCE((
                SELECT jsonb_agg(relation_id ORDER BY relation_id)
                FROM safe_relations WHERE relation_kind = 'SUPERSESSION'
            ), '[]'::jsonb),
            'tombstones', COALESCE((
                SELECT jsonb_agg(relation_id ORDER BY relation_id)
                FROM safe_relations WHERE relation_kind = 'TOMBSTONE'
            ), '[]'::jsonb)
        )::text
    END AS reconcile_json;
