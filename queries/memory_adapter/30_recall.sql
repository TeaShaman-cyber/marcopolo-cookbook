WITH params AS (
    SELECT
        convert_from(decode('{{ scope_hex }}', 'hex'), 'UTF8') AS scope,
        convert_from(decode('{{ event_id_hex }}', 'hex'), 'UTF8') AS event_id,
        convert_from(decode('{{ operation_id_hex }}', 'hex'), 'UTF8') AS operation_id,
        convert_from(decode('{{ source_class_hex }}', 'hex'), 'UTF8') AS source_class,
        convert_from(decode('{{ lifecycle_json_hex }}', 'hex'), 'UTF8')::jsonb AS lifecycle_filter,
        NULLIF(convert_from(decode('{{ created_after_hex }}', 'hex'), 'UTF8'), '')::timestamptz AS created_after,
        NULLIF(convert_from(decode('{{ created_before_hex }}', 'hex'), 'UTF8'), '')::timestamptz AS created_before,
        NULLIF(convert_from(decode('{{ cursor_created_at_hex }}', 'hex'), 'UTF8'), '')::timestamptz AS cursor_created_at,
        convert_from(decode('{{ cursor_event_id_hex }}', 'hex'), 'UTF8') AS cursor_event_id,
        {{ has_event_id }}::int AS has_event_id,
        {{ has_operation_id }}::int AS has_operation_id,
        {{ has_source_class }}::int AS has_source_class,
        {{ has_lifecycle }}::int AS has_lifecycle,
        {{ has_created_after }}::int AS has_created_after,
        {{ has_created_before }}::int AS has_created_before,
        {{ has_cursor }}::int AS has_cursor,
        {{ limit }}::int AS page_limit
), filtered AS (
    SELECT e.*
    FROM public.theseus_memory_events_v01 AS e
    CROSS JOIN params AS p
    WHERE e.scope = p.scope
      AND (p.has_event_id = 0 OR e.event_id = p.event_id)
      AND (p.has_operation_id = 0 OR e.operation_id = p.operation_id)
      AND (p.has_source_class = 0 OR e.source_class = p.source_class)
      AND (
          p.has_lifecycle = 0
          OR e.lifecycle_state IN (SELECT jsonb_array_elements_text(p.lifecycle_filter))
      )
      AND (p.has_created_after = 0 OR e.created_at >= p.created_after)
      AND (p.has_created_before = 0 OR e.created_at < p.created_before)
      AND (
          p.has_cursor = 0
          OR e.created_at < p.cursor_created_at
          OR (e.created_at = p.cursor_created_at AND e.event_id > p.cursor_event_id)
      )
), ordered_plus AS (
    SELECT
        filtered.*,
        row_number() OVER (ORDER BY created_at DESC, event_id ASC) AS rn
    FROM filtered
    ORDER BY created_at DESC, event_id ASC
    LIMIT ((SELECT page_limit FROM params) + 1)
), page AS (
    SELECT *
    FROM ordered_plus
    WHERE rn <= (SELECT page_limit FROM params)
), page_ids AS (
    SELECT event_id FROM page
), integrity_bad AS (
    SELECT 1
    FROM public.theseus_memory_relations_v01 AS r
    LEFT JOIN public.theseus_memory_events_v01 AS a
        ON a.event_id = r.endpoint_a_event_id
    LEFT JOIN public.theseus_memory_events_v01 AS b
        ON b.event_id = r.endpoint_b_event_id
    CROSS JOIN params AS p
    WHERE (
        r.endpoint_a_event_id IN (SELECT event_id FROM page_ids)
        OR r.endpoint_b_event_id IN (SELECT event_id FROM page_ids)
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
    WHERE (
        r.endpoint_a_event_id IN (SELECT event_id FROM page_ids)
        OR r.endpoint_b_event_id IN (SELECT event_id FROM page_ids)
    )
      AND r.scope = p.scope
      AND a.scope = p.scope
      AND b.scope = p.scope
), packet_parts AS (
    SELECT
        COALESCE((
            SELECT jsonb_agg(
                jsonb_build_object(
                    'event_id', event_id,
                    'operation_id', operation_id,
                    'scope', scope,
                    'source_class', source_class,
                    'lifecycle_state', lifecycle_state,
                    'created_at', to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
                    'provenance', provenance,
                    'payload', payload
                ) ORDER BY rn
            )
            FROM page
        ), '[]'::jsonb) AS items,
        COALESCE((
            SELECT jsonb_agg(
                jsonb_build_object(
                    'relation_id', relation_id,
                    'scope', scope,
                    'left_event_id', endpoint_a_event_id,
                    'right_event_id', endpoint_b_event_id,
                    'kind', 'CONTRADICTS',
                    'provenance', provenance
                ) ORDER BY relation_id
            )
            FROM safe_relations
            WHERE relation_kind = 'CONFLICT'
        ), '[]'::jsonb) AS conflicts,
        COALESCE((
            SELECT jsonb_agg(
                jsonb_build_object(
                    'relation_id', relation_id,
                    'scope', scope,
                    'superseded_event_id', endpoint_a_event_id,
                    'superseding_event_id', endpoint_b_event_id,
                    'provenance', provenance
                ) ORDER BY relation_id
            )
            FROM safe_relations
            WHERE relation_kind = 'SUPERSESSION'
        ), '[]'::jsonb) AS supersession,
        COALESCE((
            SELECT jsonb_agg(
                jsonb_build_object(
                    'relation_id', relation_id,
                    'scope', scope,
                    'target_event_id', endpoint_a_event_id,
                    'tombstone_event_id', endpoint_b_event_id,
                    'provenance', provenance
                ) ORDER BY relation_id
            )
            FROM safe_relations
            WHERE relation_kind = 'TOMBSTONE'
        ), '[]'::jsonb) AS tombstones,
        ((SELECT count(*) FROM ordered_plus) > (SELECT page_limit FROM params)) AS has_more,
        (SELECT created_at FROM page ORDER BY rn DESC LIMIT 1) AS last_created_at,
        (SELECT event_id FROM page ORDER BY rn DESC LIMIT 1) AS last_event_id
), packet_ready AS (
    SELECT
        pp.*,
        CASE
            WHEN pp.has_more AND pp.last_event_id IS NOT NULL THEN
                translate(
                    rtrim(
                        replace(
                            encode(
                                convert_to(
                                    to_char(pp.last_created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
                                    || E'\n' || pp.last_event_id,
                                    'UTF8'
                                ),
                                'base64'
                            ),
                            E'\n',
                            ''
                        ),
                        '='
                    ),
                    '+/',
                    '-_'
                )
            ELSE NULL
        END AS next_cursor
    FROM packet_parts AS pp
)
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM integrity_bad) THEN 'INTEGRITY_SCOPE_VIOLATION'
        ELSE 'OK'
    END AS status,
    CASE
        WHEN EXISTS (SELECT 1 FROM integrity_bad) THEN NULL
        ELSE jsonb_build_object(
            'core_schema_version', 'memory-core-v0.1',
            'scope', (SELECT scope FROM params),
            'items', pr.items,
            'conflicts', pr.conflicts,
            'supersession', pr.supersession,
            'tombstones', pr.tombstones,
            'next_cursor', pr.next_cursor,
            'result_state', CASE
                WHEN jsonb_array_length(pr.items) = 0 THEN 'MISS_UNKNOWN'
                WHEN jsonb_array_length(pr.conflicts) > 0 THEN 'CONFLICT'
                ELSE 'HIT'
            END
        )::text
    END AS packet_json
FROM packet_ready AS pr;
