# Workspace search

`search.sh` is the canonical text-search entry point for `/workspace` tooling.
It is a thin, explicit wrapper around the runtime-provided `ripgrep` (`rg`).

Policy:

- `rg` is primary.
- Fixed-string search is the default; regex is opt-in with `--regex`.
- Output always includes filenames and line numbers and never emits ANSI color.
- Unicode is handled by ripgrep directly.
- `--hidden` includes hidden files but still excludes `.git/`.
- There is no silent fallback to `grep`. If `rg` is unavailable, the wrapper exits `69` and prints `BLOCKED: rg unavailable`.
- `grep` remains legacy/fallback for simple pipeline filtering only, not the workspace search interface.

## Canonical recipes

Fixed string:

```bash
/workspace/tools/search/search.sh 'literal [text]' /workspace
```

Regular expression:

```bash
/workspace/tools/search/search.sh --regex 'foo[0-9]+bar' /workspace
```

Context around matches:

```bash
/workspace/tools/search/search.sh --context 3 'needle' /workspace
```

Specific extensions / globs:

```bash
/workspace/tools/search/search.sh --glob '*.py' 'needle' /workspace
/workspace/tools/search/search.sh --glob '*.md' --glob '*.txt' 'needle' /workspace
```

Hidden files, excluding `.git`:

```bash
/workspace/tools/search/search.sh --hidden 'needle' /workspace
```

Machine-readable JSON Lines:

```bash
/workspace/tools/search/search.sh --json 'needle' /workspace
```

Pattern beginning with `-`:

```bash
/workspace/tools/search/search.sh -- '--literal-leading-dash' /workspace
```

## Verification

The implementation was acceptance-tested against fixed-string metacharacters,
regex, Cyrillic Unicode text, context lines, globs, hidden-file behavior, JSON
output, and the explicit `rg unavailable` failure mode.
