# Session Search

Private local helper for the Barn Doctor-derived cumulative session-history corpus.

Session history is evidence, not semantic memory. The accepted artifacts are durable evidence; SQLite/FTS remains a regeneratable projection.

## Normal use

```bash
/workspace/tools/session-search/search.sh 'query terms'
```

This remains the one-command interactive route. `search.sh` first runs a cheap
local freshness preflight, then prefers a freshness-bound disposable local read
projection, and finally invokes the bound Session Search implementation. If the
local projection cannot be safely refreshed or validated, the wrapper emits a
`DEGRADED` notice on stderr and falls back to the explicitly bound durable corpus.
Normal search does **not** perform network access, full corpus verification, or
rebuild.

The runtime binding is loaded from `/workspace/tools/session-search/runtime.env`.
Already exported values take precedence; `runtime.env` fills only missing known
bindings so status/search/acceptance resolve the same state. The important
bindings are:

```bash
SESSION_SEARCH_CORPUS=/private/path/session-search-corpus
SESSION_SEARCH_IMPLEMENTATION_ROOT=/workspace/path/to/clean/session-search-checkout
# Optional exact/local pins:
SESSION_SEARCH_IMPLEMENTATION_HEAD=<full-git-oid>
SESSION_SEARCH_IMPLEMENTATION_REF=origin/main
# Optional local ephemeral-cache root (default: /tmp/session-search-local-projection):
SESSION_SEARCH_LOCAL_CACHE_ROOT=/tmp/session-search-local-projection
# Missing bindings are loaded from runtime.env; already exported values win.
```

`SESSION_SEARCH_IMPLEMENTATION_HEAD` makes the local preflight require an exact
checked-out commit. `SESSION_SEARCH_IMPLEMENTATION_REF` makes it compare HEAD
with the locally known ref. Neither operation performs a network refresh. When
remote freshness matters, use the workspace repository-currentness procedure
(`git fetch` plus `git-worktree-currentness.sh`) against the authoritative ref.

The wrapper is **corpus-first**. It never scans `/workspace` to guess where
private evidence lives. Corpus location resolves explicitly in this order:

1. active `SESSION_SEARCH_CORPUS` environment variable;
2. local restart-safe `runtime.env` binding;
3. deterministic `CORPUS_LOCATION_UNRESOLVED` failure.

The cheap status path observes the accepted-artifact filename set plus SQLite
projection metadata and emits a deterministic observed-generation token. This
token is a change detector; it is **not** a replacement for accepted-artifact
integrity verification.


### Local interactive projection

The durable corpus remains authority. For interactive latency only, normal
`search.sh` maintains a disposable read-only SQLite projection under local `/tmp`
storage (or `SESSION_SEARCH_LOCAL_CACHE_ROOT` when explicitly configured). The
cache is keyed to the bound corpus and is usable only when its recorded source
generation matches the currently observed accepted-artifact set and source DB
identity.

Refresh uses SQLite's backup API rather than a raw file copy. A candidate is
published only after the durable generation is stable across the snapshot, the
candidate `artifacts.sha256` set exactly matches the accepted ledger, and
`PRAGMA quick_check` returns `ok`. Concurrent refreshers serialize on a local
lock. Publication uses atomic replacement and the final cached DB is read-only.

A cache failure never widens authority and never silently serves stale bytes.
The wrapper falls back to the durable corpus and reports the degraded route on
stderr. `acceptance.sh` always verifies the durable corpus; it does not use the
interactive cache.

For deliberate local diagnostics:

```bash
/workspace/tools/session-search/status.sh --json
```

`READY` means LOCAL route coherence only. It does not mean GitHub was consulted
and does not mean the corpus passed full verification. Remote currentness uses
the existing workspace repository-currentness route; `acceptance.sh` remains
the heavier integrity/rebuild path.

For a deliberate legacy/scratch projection, bypass the wrapper and use the
module directly with `--db PATH`; that path is outside the normal runtime
freshness contract.

### Runtime helper projection

The tracked helper source lives in `marcopolo-cookbook/session-search/`. Project
it into `/workspace/tools/session-search` with:

```bash
/workspace/marcopolo-cookbook/session-search/materialize-runtime.sh --ref origin/main
```

For an operational projection, materialize from the same selected Git ref that
preflight will verify. The no-`--ref` form remains available for deliberate
branch/development worktree testing. The materializer replaces only tracked helper
files and deliberately preserves the local/private `runtime.env`. Runtime helpers
verify themselves against the
selected local Git ref (`SESSION_SEARCH_CANONICAL_REF`, default `origin/main`)
when the canonical cookbook source is Git-backed. The checkout HEAD is reported
separately and is not freshness authority. Ordinary preflight performs no fetch;
remote freshness remains the explicit repository-currentness step. Non-Git
canonical directories retain direct file-comparison fallback semantics.

## Reference discovery

Do not start troubleshooting by recursively traversing `/workspace` or network-backed storage. Inspect `/workspace/tools` and use the canonical bounded search wrapper described by the cookbook:

```bash
/workspace/tools/search/search.sh --help
/workspace/tools/search/search.sh 'literal text' path/to/bounded/root
```

The Session Search wrapper performs no network access and no durable-corpus
writes. Normal search may maintain the disposable local `/tmp` read projection
described above.

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
