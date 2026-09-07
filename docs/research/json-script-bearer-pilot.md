# Pilot design v2: JSON managed secret -> ephemeral env -> mcporter

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

Codex review found that dispatching JSON immediately after starting Script can misclassify a startup race as network isolation.

The handler must acknowledge readiness only **after the listener has successfully bound**. The harness must wait for that acknowledgment with a bounded timeout before invoking JSON.

The readiness channel contains no secret. A fresh non-secret marker/nonce may be used to distinguish the current run from stale state. Failure to obtain READY is a Script-startup failure, not Gate 0 network-isolation evidence.

## 7. Gate order

### Gate R — listener readiness

Postcondition:

```text
script_listener_bound = true
```

If READY is not observed within the bounded timeout, STOP as `SCRIPT_NOT_READY`.

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

### Gate 4 — execution-boundary visibility

The security claim requires more than “the token was not persisted.” A child environment is acceptable only if the ordinary workspace/model execution plane cannot read the executor's credential-bearing process environment while the run is live.

Using the synthetic marker only, the pilot should attempt a bounded workspace-side visibility probe when the relevant process identity is observable. Outcomes are explicit:

```text
workspace cannot address/read executor process env -> ISOLATION_NOT_OBSERVED_AS_BROKEN
workspace can read synthetic token from process env -> FAIL_SECRET_VISIBLE_TO_WORKSPACE
process identity/surface not observable            -> UNKNOWN
```

`UNKNOWN` is not silently converted into a secure-isolation PASS.

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

Do not collapse functional transport and isolation into one boolean.

### Transport PASS

All must hold:

```text
script_listener_bound  = true
json_to_script         = true
basic_received         = true
mcporter_called        = true
bearer_matches_basic   = true
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

### Isolation status

Report independently:

```text
VERIFIED_NOT_WORKSPACE_READABLE
FAIL_SECRET_VISIBLE_TO_WORKSPACE
UNKNOWN
```

A useful first run may therefore produce:

```text
transport               = PASS
observable_non_disclosure = PASS
executor_isolation       = UNKNOWN
```

That is evidence, but it is not yet equivalent to a production-secret approval.

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

The outer acceptance harness adds leakage and isolation verdicts after its own checks.

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
- one non-secret readiness acknowledgment;
- bounded timeouts and one-shot shutdown;
- request/header debug logging disabled;
- Script shell mode off;
- no persistent daemon and no secret-bearing temp file.

The pilot uses the static non-secret mcporter definition above. Its exact serialization is owned by mcporter rather than reimplemented by the handler; setup verification is a config readback showing the fixed endpoint and symbolic environment reference only.

## 12. Failure classification

```text
SCRIPT_NOT_READY
  -> handler startup/bind problem

JSON_TO_SCRIPT_UNREACHABLE
  -> network/executor boundary after confirmed readiness

BASIC_MISSING_OR_MALFORMED
  -> JSON auth injection/request contract

MCPORTER_ENV_REFERENCE_UNSUPPORTED
  -> mcporter configuration/expansion contract

BEARER_MISMATCH
  -> env-to-client transport defect

SECRET_PERSISTED_OR_REFLECTED
  -> disclosure defect

SECRET_VISIBLE_TO_WORKSPACE_PROCESS_INSPECTION
  -> executor isolation defect
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
- Script self-orchestration of MarcoPolo connections.

Those require fresh evidence and a separate decision after this primitive is understood.

## 14. Design acceptance condition

The design is ready for an implementation plan when reviewers agree that:

1. the central primitive is `managed secret -> ephemeral child env`, not a custom Basic-to-Bearer service;
2. Hermes is used only as a reference for env-reference-to-header composition;
3. readiness removes the startup-race false negative before Gate 0;
4. leakage scanning includes recoverable Basic Base64 representations;
5. functional transport, observable non-disclosure, and executor isolation are reported separately;
6. no component exists without an evidence-backed reason;
7. a failed gate stops rather than spawning a vault/daemon/relay fallback.
