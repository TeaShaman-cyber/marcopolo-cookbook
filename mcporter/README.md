# MarcoPolo mcporter workbench

Persistent MCP inspection and call workbench for this MarcoPolo runtime.

## Runtime contract

- Root: `/workspace/tools/mcporter`
- MarcoPolo system Node remains platform-owned (currently Node 22).
- Private tool runtime: Node `v24.20.0`.
- mcporter pinned: `0.13.8`.
- Build/install happens on local `/tmp`; NFS stores only a single runtime archive plus checksum.
- The wrapper expands that archive into a local `/tmp` cache on demand; system Node/npm are not modified.
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

## Private runtime / tmpfs-proxy pattern

Large dependency trees should not be installed or replaced in place on `/workspace` NFS. Build the complete runtime in local `/tmp`, verify it there, persist one compressed archive plus SHA-256 under `runtime/bundles/`, and expand it back into `/tmp` on demand. This avoids npm cleanup races and silent partial NFS trees.

The canonical installer is `scripts/install-runtime.sh`; cache restoration is `scripts/ensure-runtime.sh`. The exact Node version, Node upstream SHA-256, mcporter version, and bundle id are declared in `runtime/versions.env`.

## Upgrade rule

Do not silently upgrade. Update the declared Node/mcporter pins, build a new bundle in `/tmp`, run `tests/acceptance.sh`, and run a real MCP regression probe before switching the documented bundle id. Do not replace MarcoPolo's system Node for one tool.

## Acceptance

```bash
./tests/acceptance.sh
```

A passing local acceptance proves the workbench installation, wrapper, README, lockfile, config parsing, and CLI startup. It does not prove any particular external MCP server is authenticated or healthy.

## Wolfram 503 regression

`mcporter 0.9.0` on Node 22 misclassified a real Wolfram Cloud `HTTP 503 Scheduled Upgrade` as `OAuth authorization required`. Raw MCP and MCPJam CLI showed OAuth was not required. `mcporter 0.13.8` under private Node 24 correctly preserves the 503 as a transport/version-negotiation failure. Unexpected auth prompts should therefore be cross-checked against raw HTTP/MCP or an independent client.
