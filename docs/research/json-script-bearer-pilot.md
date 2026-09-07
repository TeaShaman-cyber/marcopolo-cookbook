# Pilot design v3: JSON managed secret -> ephemeral env -> mcporter

Related: #13

Status: **design / consultation only**. No production secret and no real provider are in scope.

## 1. Research question

Can MarcoPolo's existing `json` connection credential boundary act as an **out-of-workspace secret source** for one bounded Script capability, with the secret projected only into a child-process environment and then consumed by `mcporter` through a symbolic environment reference?

The pilot tests this primitive:

```text
MarcoPolo managed JSON secret
        -> HTTP Basic transport
        -> Script receives password in RAM
        -> child-only environment variable
        -> mcporter symbolic header reference
        -> HTTP Bearer on the wire
```

It does **not** build a vault, keychain service, generic Basic-to-Bearer proxy, persistent broker, or provider integration.

## 2. What changed from v1

The first design described the Script component as a Basic-to-Bearer bridge. That is more responsibility than the evidence requires.

The tighter abstraction is:

```text
managed secret -> ephemeral env adapter
```

Bearer construction belongs to the consumer configuration, not to the adapter.

This is informed by Hermes Agent's MCP configuration pattern: Hermes allows environment references such as `${VAR}` / `${env:VAR}` in MCP string fields, including HTTP headers, and its tests exercise `Authorization: Bearer ${MCP_GH_API_KEY}` expanding from environment state. Hermes is a **reference pattern, not a dependency** and not evidence that MarcoPolo shares Hermes's secret-scope implementation.

Reference snapshot used for the design:

- repository: `NousResearch/hermes-agent`
- commit: `233757037df1f03f9fe1cfddc097acd5ad7f7510`
- `website/docs/reference/mcp-config-reference.md`: HTTP `headers` plus `${VAR}` / `${env:VAR}` expansion across server string values;
- `tests/cli/test_cli_mcp_config_watch.py`: concrete `Authorization: Bearer ${MCP_GH_API_KEY}` fixture;
- `hermes_cli/config.py`: recursive environment-reference expansion and external-secret-source handling.

The reusable idea is only:

```text
secret source -> process environment -> declarative client config -> Authorization header
```

For this pilot, MarcoPolo JSON replaces the upstream secret source and `mcporter` replaces Hermes's MCP transport.

### MarcoPolo implementation references

The next design/review pass is grounded in Immersa's public implementation repositories rather than inferred platform behavior:

- `immersa-co/marcopolo-plugin@113b842f35c875a2d8ab5b31eb00675e65cd307c` — exposed plugin/session contract, including the remote `/workspace` surface, `workspace_shell`, product data tools, and browser-based credentialed connection setup;
- `immersa-co/marcopolo-python-sdk@a2ba6fd7ec6963185be91b450a03639e5bc56749` — public API client and connection-setup contract;
- `immersa-co/marcopolo-integration-starter@fa8bc2df16057162861a066cb007780219063081` — production-facing reference integration, including namespace-key exchange for short-lived user tokens and SDK/API-backed connection management.

These repositories are authoritative for the public/exposed behavior they implement. They do **not** expose the MarcoPolo backend credential-store implementation, so this pilot makes no claim about a specific encryption-at-rest mechanism. The directly observed claim remains narrower: the managed JSON password is not stored as ordinary plaintext in `/workspace`, and the pilot tests whether it can be consumed without re-materializing it into observable persistent workspace surfaces.

## 3. Already observed

The preceding #13 work established with synthetic values:

1. A MarcoPolo `json` connection can store a Basic-auth password in a managed secret field and inject it into an HTTP request.
2. A `.json` query file containing `url` is a working JSON-connection query contract.
3. JSON connection output can later be processed by Script Connection.
4. Output-mediated credential reflection is unsuitable for real secrets because reflected auth can enter connection results and DuckDB.
5. Script Connection can execute a bounded workspace wrapper with shell mode off.
6. The installed `mcporter` documents HTTP header values that reference environment variables, including `${VAR}` and `$env:VAR` forms.

Therefore the secret must travel through the authenticated request boundary into Script memory, not through a connector result row.

## 4. Feynman / Five-Whys guard

Each component must answer one observable need.

```text
Why JSON connector?
  -> verified managed-secret storage/injection outside /workspace.

Why one HTTP listener?
  -> Basic request auth is the currently exposed way to carry that managed password to Script execution.

Why Script Connection?
  -> verified local capability execution and child-process boundary.

Why child env?
  -> mcporter already supports symbolic environment references; no reason to construct Bearer in Script logic.

Why mcporter?
  -> the intended use is authenticated MCP tooling; env presence alone does not prove the client sends the credential.

Why a fake MCP endpoint?
  -> it proves the same bytes emerge from mcporter as Bearer without involving a real provider.
```

Five Whys is applied only after a concrete failed gate. Stop when the next answer would be speculation. Fix or probe the smallest responsible boundary first.

A failed gate does **not** authorize adding Infisical, another vault, a daemon, relay, tunnel, generic forward proxy, or second secret store.

## 5. Minimal architecture

One Script-side process performs the adapter and synthetic endpoint roles:

```text
                         one Script process
                       +-------------------------+
JSON connection ------>| /ingest                 |
 managed password       |   Basic                 |
 injected server-side   |     -> password in RAM  |
                       |          |               |
                       |          v child env     |
                       |       PILOT_TOKEN         |
                       |          |               |
                       |          v               |
                       |       mcporter           |
                       |          |               |
                       |          | config says   |
                       |          | Bearer ${...} |
                       |          v               |
                       | /mcp <- Authorization    |
                       |        Bearer ...        |
                       | compare in RAM           |
                       +------------+------------+
                                    |
                                    v
                              safe receipt
```

There is no separate Basic-to-Bearer bridge. The Script adapter only maps the captured password to a child environment variable.

There is no separate fake-MCP process. The same process can serve `/ingest` and the minimal `/mcp` contract concurrently.

There is no secret-bearing mcporter configuration. The pilot uses one project-local mcporter definition containing only the fixed synthetic endpoint and a symbolic environment reference. It is created and read back through mcporter's own config surface before the acceptance run; no per-run config generation is required, and no credential value is stored in it.

## 6. Orchestration boundary

The acceptance harness orchestrates MarcoPolo connections from outside the Script process:

```text
harness
  -> starts Script Connection query in background
  -> waits for bounded non-secret READY acknowledgment
  -> invokes JSON connection query
  -> waits for Script receipt
  -> runs observable leakage checks
```

The Script process does **not** need to invoke `connection query` itself. That control-plane dependency is outside the transport hypothesis and is removed from the pilot.

### Readiness acknowledgment

Codex review found that dispatching JSON immediately after starting Script can misclassify a startup race as network isolation, and then correctly challenged v2 for not naming an observable READY channel.

V3 makes that channel concrete and non-secret. The harness generates a fresh run nonce and starts Script with that nonce as a harmless argument. After the listener has successfully bound, the handler atomically creates exactly one marker such as:

```text
/workspace/artifacts/json-secret-env-pilot/ready-<run_nonce>
```

with fixed content `READY`. The harness bounded-polls that exact path through the ordinary workspace surface before invoking JSON. The unique nonce prevents a stale marker from satisfying a new run; the harness removes the marker during cleanup.

The marker contains no credential material. If the Script execution plane cannot create a marker that the workspace plane can read, STOP as `READY_CHANNEL_UNAVAILABLE`. That is a concrete capability failure, not evidence of JSON-to-Script network isolation and not justification for adding a broker.

## 7. Gate order

### Gate R — listener readiness

Postconditions:

```text
script_listener_bound    = true
ready_marker_observable  = true
```

The marker is created only after successful bind. If Script cannot bind, STOP as `SCRIPT_NOT_READY`. If it binds but the nonce-scoped marker is not observable through `/workspace`, STOP as `READY_CHANNEL_UNAVAILABLE`. Only after both conditions hold may Gate 0 run.

### Gate 0 — JSON-to-Script reachability

Only after READY:

```text
JSON executor -> Script /ingest
```

This boundary remains **UNKNOWN** until runtime acceptance. If it fails after confirmed readiness, record `JSON_TO_SCRIPT_UNREACHABLE` and STOP. Do not add relay or tunneling machinery inside this pilot.

### Gate 1 — managed Basic secret -> Script RAM

`/ingest` accepts one expected Basic-auth request, decodes it in memory, retains only the password for the current run, and returns a sanitized non-secret acknowledgment.

The JSON response must not reflect `Authorization`, username/password, or derived credential material.

### Gate 2 — Script RAM -> child env -> mcporter -> Bearer

The adapter constructs a child environment mapping without mutating global process environment unnecessarily:

```text
PILOT_TOKEN=<captured password>
```

`mcporter` receives no plaintext token in argv. Its MCP definition contains only a symbolic reference equivalent to:

```text
Authorization: Bearer ${PILOT_TOKEN}
```

The fake `/mcp` endpoint succeeds only if the Bearer token exactly equals the password captured at Gate 1.

This proves transport equality:

```text
Basic password bytes == mcporter Bearer token bytes
```

It does not by itself prove secret isolation from every platform-internal surface.

### Gate 3 — observable leakage scan

Codex review found that plaintext-only scanning is insufficient because Basic auth embeds `username:password` inside Base64.

For the synthetic run, the harness derives scan signatures only in transient test memory and searches all observable surfaces for at least:

```text
password plaintext
username:password
base64(username:password)
Basic <base64(username:password)>
Bearer <password>
```

Also scan any additional exact serialization that the acceptance harness itself emits. Derived signatures must not be committed or included in receipts.

Observable targets include, where accessible:

```text
/workspace pilot paths
connection stdout/stderr
connection result payloads
DuckDB relation rows/metadata reachable through the normal workspace surface
mcporter logs/traces produced by the pilot
process argv visible from the workspace execution plane
shell history or generated command files
```

Platform-internal logs, executor memory, or process tables that are not exposed to the workspace remain `UNKNOWN`; absence from visible surfaces must not be promoted to a claim about inaccessible internals.

### Phase-1 scope boundary

This pilot does **not** attempt to prove complete executor/process-environment isolation. Codex correctly noted that v2's proposed live-process probe required extra synchronization and could overstate a negative observation as verified isolation. That question is deferred to a separate platform-boundary experiment if Phase 1 succeeds.

For Phase 1, inaccessible platform-internal logs, executor memory, and process-environment surfaces remain explicitly `UNKNOWN`. No production-security verdict is derived from their absence in the observable workspace plane.

## 8. Secret boundary

Allowed transient locations for the synthetic pilot:

```text
MarcoPolo managed JSON credential field
JSON executor request Authorization state
Script handler process memory
mcporter child environment
mcporter outbound Authorization header
fake MCP handler memory
```

Forbidden persistent/model-visible locations:

```text
Git repository
/workspace credential-bearing files
JSON query files
Script query arguments
mcporter argv
mcporter config values
stdout/stderr
connection result payload
DuckDB rows containing credential material
trace/record output
shell history
Issue / PR / review text
```

The repository may contain only the **name** of the environment variable and the symbolic header template, never its value.

## 9. Verdict model

Phase 1 has exactly two verdicts plus explicit unknowns; it does not claim executor isolation.

### Transport PASS

All must hold:

```text
script_listener_bound   = true
ready_marker_observable = true
json_to_script          = true
basic_received          = true
mcporter_called         = true
bearer_matches_basic    = true
```

### Observable non-disclosure PASS

All observable scans must be clean for plaintext and encoded forms:

```text
secret_in_workspace    = false
secret_in_result       = false
secret_in_duckdb       = false
secret_in_argv         = false   # where observable
secret_in_logs         = false
basic_encoding_leak    = false
bearer_header_leak     = false
```

### Explicit UNKNOWN boundary

```text
platform_internal_logs        = UNKNOWN
executor_memory               = UNKNOWN
executor_process_environment  = UNKNOWN
credential_store_at_rest_impl = UNKNOWN
```

A successful Phase 1 therefore means only:

```text
transport                 = PASS
observable_non_disclosure = PASS
```

It does not equal a production-secret approval.

## 10. Receipt contract

The Script result contains booleans/status only, for example:

```json
{
  "listener_ready": true,
  "json_to_script": true,
  "basic_received": true,
  "mcporter_called": true,
  "bearer_matches_basic": true
}
```

The outer acceptance harness adds the observable leakage verdict after its own checks; platform-internal isolation remains outside Phase 1.

Never emit:

```text
Authorization header
Basic payload
Bearer value
secret hash/fingerprint
encoded username:password
child environment dump
```

A hash is unnecessary: equality is tested entirely inside the synthetic handler.

## 11. Implementation shape, not implementation

If the gates remain viable, the implementation should stay intentionally small:

- one Python handler;
- standard-library concurrent HTTP serving is sufficient;
- one `/ingest` route;
- one minimal `/mcp` route implementing only the MCP exchange required by one `probe` call;
- one child `mcporter` invocation;
- one symbolic environment variable name;
- one nonce-scoped non-secret READY marker created after listener bind and removed during cleanup;
- bounded timeouts and one-shot shutdown;
- request/header debug logging disabled;
- Script shell mode off;
- no persistent daemon and no secret-bearing temp file.

The pilot uses the static non-secret mcporter definition above. Its exact serialization is owned by mcporter rather than reimplemented by the handler; setup verification is a config readback showing the fixed endpoint and symbolic environment reference only.

## 12. Failure classification

```text
SCRIPT_NOT_READY
  -> handler startup/bind problem

READY_CHANNEL_UNAVAILABLE
  -> Script listener may be bound, but the nonce-scoped non-secret marker is not observable through /workspace

JSON_TO_SCRIPT_UNREACHABLE
  -> network/executor boundary after confirmed readiness

BASIC_MISSING_OR_MALFORMED
  -> JSON auth injection/request contract

MCPORTER_ENV_REFERENCE_UNSUPPORTED
  -> mcporter configuration/expansion contract

BEARER_MISMATCH
  -> env-to-client transport defect

SECRET_PERSISTED_OR_REFLECTED
  -> observable disclosure defect
```

Each failure stops the pilot. Five Whys then starts from that observed symptom. No automatic architecture expansion follows from a failure code.

## 13. Non-goals

This pilot does not decide:

- production provider selection;
- Buffer or Notion integration;
- OAuth refresh flows;
- multiple simultaneous credentials;
- secret rotation protocol;
- generic secret references;
- a persistent local broker;
- a vault replacement;
- remote relay/tunnel architecture;
- Script self-orchestration of MarcoPolo connections;
- full executor/process-environment isolation;
- backend credential-store encryption implementation audit.

Those require fresh evidence and a separate decision after this primitive is understood.

## 14. Design acceptance condition

The design is ready for an implementation plan when reviewers agree that:

1. the central primitive is `managed secret -> ephemeral child env`, not a custom Basic-to-Bearer service;
2. Hermes is used only as a reference for env-reference-to-header composition;
3. readiness uses the concrete nonce-scoped `/workspace` marker channel and therefore removes the startup-race false negative before Gate 0 without a new service;
4. leakage scanning includes recoverable Basic Base64 representations;
5. Phase 1 reports only transport and observable non-disclosure, while inaccessible executor/platform surfaces remain `UNKNOWN`;
6. the public Immersa repositories are cited for exposed behavior, while backend credential-store guarantees are not inferred from them;
7. no component exists without an evidence-backed reason;
8. a failed gate stops rather than spawning a vault/daemon/relay fallback.
