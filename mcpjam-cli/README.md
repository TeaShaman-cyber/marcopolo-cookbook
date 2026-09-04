# MarcoPolo MCPJam CLI workbench

Lightweight second MCP client for bounded diagnostics in the MarcoPolo runtime.

## Runtime contract

- Root: `/workspace/tools/mcpjam-cli`
- Node supplied by MarcoPolo: Node 22
- Package: `@mcpjam/cli`
- Pin: `5.6.0`
- Wrapper: `/workspace/tools/mcpjam-cli/bin/mcpjam`
- Generated `node_modules/` is local runtime state and is not committed.

This workbench is intentionally the CLI package, not the full `@mcpjam/inspector` UI package. The full Inspector dependency graph is much larger and proved unsuitable for this runtime during the 2026-09-04 investigation; see cookbook issue #8.

## Why keep a second MCP client?

A second implementation helps distinguish provider/transport failures from client interpretation bugs.

Verified example on 2026-09-04:

```text
Wolfram Cloud MCP endpoint
  -> raw HTTP initialize: 503 Scheduled Upgrade
  -> MCPJam CLI: 503 Service Unavailable, oauth.required=false
  -> mcporter 0.9.0: incorrectly entered OAuth authorization flow
```

Therefore an OAuth prompt from one client is not by itself evidence that the server requires OAuth.

## Quick start

```bash
cd /workspace/tools/mcpjam-cli
./bin/mcpjam --help
./bin/mcpjam server probe --help
./bin/mcpjam tools --help
./bin/mcpjam skills --help
```

Probe a remote HTTP MCP endpoint without interactive auth:

```bash
./bin/mcpjam --format json server probe \
  --url https://agenttools.wolfram.com/mcp \
  --timeout 10000 \
  --retries 0
```

## Skills boundary

`mcpjam skills` inspects Agent Skills served by an MCP server via SEP-2640 (`list`, `get`, `read`).

The MCPJam upstream repository also contains SDK authoring/evaluation skills, including `sdk/skills/create-mcp-eval` and `sdk/skills/explore-to-sdk-evals`. Treat those as upstream reference material with explicit provenance rather than silently copying them into this cookbook.

## Acceptance

```bash
./tests/acceptance.sh
```

A passing acceptance proves the pinned CLI is installed and that the probe and skills command surfaces are available. It does not prove any external MCP provider is healthy.

## Upgrade rule

Do not silently upgrade. Check the published `@mcpjam/cli` version and Node engine, update the exact pin and lockfile intentionally, then run acceptance before committing.
