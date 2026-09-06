CREATE TABLE IF NOT EXISTS public.theseus_memory_events_v01 (
    operation_id TEXT PRIMARY KEY,
    request_fingerprint TEXT NOT NULL,
    event_id TEXT NOT NULL UNIQUE,
    scope TEXT NOT NULL,
    source_class TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL CHECK (
        lifecycle_state IN ('OBSERVED', 'CANDIDATE', 'PENDING', 'SUPERSEDED', 'TOMBSTONED')
    ),
    created_at TIMESTAMPTZ NOT NULL,
    provenance JSONB NOT NULL,
    payload JSONB NOT NULL,
    committed_at TIMESTAMPTZ NOT NULL,
    receipt JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS theseus_memory_events_v01_scope_order_idx
    ON public.theseus_memory_events_v01(scope, created_at DESC, event_id ASC);

CREATE TABLE IF NOT EXISTS public.theseus_memory_relations_v01 (
    relation_id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    relation_kind TEXT NOT NULL CHECK (
        relation_kind IN ('CONFLICT', 'SUPERSESSION', 'TOMBSTONE')
    ),
    endpoint_a_event_id TEXT NOT NULL REFERENCES public.theseus_memory_events_v01(event_id),
    endpoint_b_event_id TEXT NOT NULL REFERENCES public.theseus_memory_events_v01(event_id),
    provenance JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS theseus_memory_relations_v01_a_idx
    ON public.theseus_memory_relations_v01(endpoint_a_event_id);
CREATE INDEX IF NOT EXISTS theseus_memory_relations_v01_b_idx
    ON public.theseus_memory_relations_v01(endpoint_b_event_id);
CREATE INDEX IF NOT EXISTS theseus_memory_relations_v01_scope_idx
    ON public.theseus_memory_relations_v01(scope, relation_kind, relation_id);

SELECT
    'OK'::text AS status,
    to_regclass('public.theseus_memory_events_v01')::text AS events_table,
    to_regclass('public.theseus_memory_relations_v01')::text AS relations_table;
