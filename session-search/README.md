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

## Recover a Barn Doctor export from Google Drive through MarcoPolo

When an exported session ZIP lives in the connected Google Drive, keep the bytes in the MarcoPolo runtime instead of trying to bridge them through ChatGPT `/mnt/data`.

1. Confirm the Drive connection and capabilities:

```bash
connection list
connection test <drive-connection> --json
```

2. Resolve the provider folder ID from the Drive root. A display name such as `Theseus Bridge` is not itself a parent ID:

```bash
connection browse <drive-connection> --remote-path / --detailed
```

3. Browse the resolved folder ID when discovery is needed:

```bash
connection browse <drive-connection> --remote-path <folder-id> --detailed
```

`browse` may show only a preview even when the returned `row_count` is larger. Preview truncation is not evidence that a file is absent.

4. If the exact filename is known, download it directly. Prefer the connection-managed destination unless a custom path is known writable:

```bash
connection download <drive-connection> \
  --remote-path barn-doctor-doctor-<capture-id>.zip \
  --json
```

The default destination is under:

```text
/workspace/data/downloads/<connection-name>/
```

A custom `--local-path` can fail with a local permission error after the remote file has already resolved. Treat that as a destination-runtime problem, not a Drive lookup failure.

5. Verify the downloaded evidence before indexing:

```bash
sha256sum /workspace/data/downloads/<connection-name>/<capture>.zip
unzip -l /workspace/data/downloads/<connection-name>/<capture>.zip
```

6. Run the normal importer/search path only if the artifact satisfies the Session Search contract. `BLOCKED_MIXED_SESSION_ARTIFACT` is fail-closed evidence; do not delete members by title, timestamp, filename order, or guesswork. Use the provenance-aware recovery contract tracked in `theseus-session-search-lab#16` when a capture contains unrelated provider fetches.

### Archive rebuilding caveat

Do not assume the `zip` CLI exists in MarcoPolo. Barn Doctor ZIP entries can also carry timestamps that Python considers earlier than 1980. When a reviewed recovery workflow needs to build a derived ZIP, use Python `zipfile` with `strict_timestamps=False`, keep the immutable source ZIP unchanged, and record source/derived hashes plus the exact provenance rule used for member selection.
