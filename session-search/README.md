# Session Search

Private local helper for the Barn Doctor-derived session-search corpus.

```bash
/workspace/tools/session-search/search.sh 'query terms'
```

The wrapper performs no network access and no persistence writes. Source authority remains the immutable Barn Doctor export; the SQLite FTS5 DB is regeneratable.
