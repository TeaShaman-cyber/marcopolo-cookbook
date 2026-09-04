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
