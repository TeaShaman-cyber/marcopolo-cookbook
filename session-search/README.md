# Session Search

Private local helper for the Barn Doctor-derived cumulative session-history corpus.

Session history is evidence, not semantic memory. The accepted artifacts are durable evidence; SQLite/FTS remains a regeneratable projection.

## Normal use

```bash
/workspace/tools/session-search/search.sh 'query terms'
```

The wrapper is **corpus-first**. It never scans `/workspace` to guess where private evidence lives. Corpus location resolves explicitly in this order:

1. active `SESSION_SEARCH_CORPUS` environment variable;
2. local restart-safe `/workspace/tools/session-search/runtime.env` binding;
3. deterministic `CORPUS_LOCATION_UNRESOLVED` failure.

Example local binding (do not commit private paths):

```bash
cat > /workspace/tools/session-search/runtime.env <<'EOF'
SESSION_SEARCH_CORPUS=/private/path/session-search-corpus
export SESSION_SEARCH_CORPUS
EOF
chmod 600 /workspace/tools/session-search/runtime.env
```

An explicitly exported `SESSION_SEARCH_CORPUS` wins over `runtime.env`. The wrapper validates the cumulative corpus markers before invoking `session_search.search --corpus`.

For a deliberate legacy/scratch projection, bypass the wrapper and use the module directly with `--db PATH`.

## Reference discovery

Do not start troubleshooting by recursively traversing `/workspace` or network-backed storage. Inspect `/workspace/tools` and use the canonical bounded search wrapper described by the cookbook:

```bash
/workspace/tools/search/search.sh --help
/workspace/tools/search/search.sh 'literal text' path/to/bounded/root
```

The Session Search wrapper performs no network access and no persistence writes.

## Operational acceptance

Use the acceptance runner when Session Search looks stale, after a runtime restart, after changing the corpus binding, or before declaring an import healthy:

```bash
/workspace/tools/session-search/acceptance.sh
```

The default mode is read-only against the live corpus. Its sequence is:

```text
health / corpus binding
→ verify accepted evidence and live projection
→ global search
→ session-scoped search using a returned session id
→ rebuild a temporary projection from copied artifacts + accepted ledger
→ compare rebuilt counts/integrity with live verify
```

The rebuild step never mutates the live corpus. It creates a temporary corpus from durable evidence and deletes it after verification.

To explicitly test an import, supply the archive path:

```bash
/workspace/tools/session-search/acceptance.sh --ingest /path/to/export.zip
```

`--ingest` is the only acceptance mode allowed to mutate the live corpus. Re-ingesting an already accepted artifact is expected to be an idempotent `ALREADY_INGESTED` or equivalent verified no-op, followed by a fresh verify.

Useful fail-closed states include:

- `CORPUS_LOCATION_UNRESOLVED` — neither the environment nor `runtime.env` resolved the corpus;
- `CORPUS_UNAVAILABLE` — the configured cumulative corpus markers are missing;
- `INGEST_PATH_UNRESOLVED` / `INGEST_PATH_UNREADABLE` — explicit ingest was requested without a usable artifact;
- `SEARCH_NO_HITS` — the acceptance query cannot produce a session for the session-scoped check;
- `REBUILD_MISMATCH` — projection rebuilt from durable evidence disagrees with the live projection.

Known traps:

- do not troubleshoot by recursively scanning `/workspace` for a corpus;
- do not point the normal wrapper at a legacy `--db` projection;
- do not run live `corpus rebuild` merely as a health check;
- do not treat transport ZIP SHA and normalized accepted artifact SHA as the same identity;
- do not repeat a large MarcoPolo shell payload after a pre-execution 403; split it into bounded commands.
