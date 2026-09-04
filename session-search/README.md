# Session Search

Private local helper for the Barn Doctor-derived session-search corpus.

```bash
/workspace/tools/session-search/search.sh 'query terms'
```

The wrapper performs no network access and no persistence writes. Source authority remains the immutable Barn Doctor export; the SQLite FTS5 DB is regeneratable.

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
