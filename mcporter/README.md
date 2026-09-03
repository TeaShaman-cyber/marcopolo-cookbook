# MarcoPolo mcporter workbench

Persistent MCP inspection and call workbench for this MarcoPolo runtime.

## Runtime contract

- Root: `/workspace/tools/mcporter`
- Node supplied by MarcoPolo: Node 22
- mcporter pinned: `0.9.0` (newest release currently declaring Node >=20.11 support)
- Install is local to this directory; system Node/npm are not modified.
- Wrapper: `/workspace/tools/mcporter/bin/mcporter`
- Config: `/workspace/tools/mcporter/config/mcporter.json`
- Secrets do not belong in README, committed config, examples, or traces.

## Boundary

Success through mcporter proves capability only inside the MarcoPolo runtime. It does not prove the same MCP capability exists in ChatGPT, Codex, or another runtime. Transport/access also does not establish authority over the underlying data.

Default posture is read-only discovery and inspection. Stateful or externally consequential calls require an explicit reason and the applicable permission gate.

## Quick start

```bash
cd /workspace/tools/mcporter
./bin/mcporter --version
./bin/mcporter list --json
./bin/mcporter list <server> --schema
./bin/mcporter call <server.tool> key:value
```

Inventory:

```bash
./scripts/inventory.sh
```

## Adding a server

Prefer mcporter's own config interface rather than hand-editing opaque generated state:

```bash
./bin/mcporter config --help
```

Keep non-secret server definitions in `config/mcporter.json`. Credentials should use the provider/runtime credential mechanism rather than plaintext files here.

## Diagnostic flow

```text
identify server
-> inspect config
-> list server / schema
-> choose smallest read-only probe
-> call
-> verify returned evidence
-> only then consider broader or stateful actions
```

Do not infer `server absent` from one failed call. Distinguish configuration missing, authentication failure, transport failure, schema mismatch, provider failure, and tool-level error.

## Traces

`traces/` is for compact receipts only: command class, server/tool name, timestamps, exit status, small normalized result metadata, and provenance. Do not persist large raw payloads or secrets.

## Upgrade rule

Do not silently upgrade. Check `npm view mcporter version engines --json`, compare required Node version and CLI surface, then run `tests/acceptance.sh`. If a newer release requires Node 24+, either keep the pin or create an isolated runtime intentionally; do not replace MarcoPolo's system Node just for mcporter.

## Acceptance

```bash
./tests/acceptance.sh
```

A passing local acceptance proves the workbench installation, wrapper, README, lockfile, config parsing, and CLI startup. It does not prove any particular external MCP server is authenticated or healthy.
