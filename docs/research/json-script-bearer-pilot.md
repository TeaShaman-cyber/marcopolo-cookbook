# Pilot design: JSON connector -> Script -> Bearer -> mcporter

Related: #13

Status: **design / consultation only**. No production secret and no real provider are in scope.

## Research question

Can MarcoPolo's existing `json` connection credential boundary be reused to hand a synthetic secret to a Script-side processor via HTTP Basic, then pass the same bytes to `mcporter` as an HTTP Bearer token **without materializing the secret in `/workspace`, DuckDB, stdout/stderr, argv, or persistent config**?

This pilot tests the transport primitive only. It does not build a general keychain, proxy, vault, or provider integration.

## Already observed

The preceding #13 research established these facts with synthetic values:

1. A MarcoPolo `json` connection can store a Basic-auth password in its managed secret field and inject it into an HTTP request.
2. A `.json` query file with a `url` field is a working query contract for this connection.
3. JSON query output can be processed later by Script Connection, but that output-mediated path is **not acceptable for real secrets** because reflected credentials can enter result/DuckDB state.
4. Script Connection can execute a bounded workspace wrapper with shell mode off.
5. `mcporter config add --header` supports environment-variable expansion such as `${VAR}` / `$env:VAR`.

The pilot therefore must deliver the synthetic value to Script through a request boundary, not through a connector result row.

## Feynman / Five-Whys guard

The pilot deliberately starts from the smallest mechanism that can falsify the idea.

```text
Why JSON connector?
  -> it is the verified managed-secret injection boundary.

Why an HTTP receiver?
  -> JSON exposes the managed password through Basic request auth; no credential_ref -> local exec primitive is currently exposed.

Why Script Connection?
  -> it is the verified local capability layer that can host the processor and invoke mcporter.

Why mcporter?
  -> the target use case is authenticated MCP/API tooling; the pilot must prove the translation reaches the actual client boundary.

Why a fake MCP endpoint?
  -> presence of an environment variable alone does not prove mcporter emitted the corresponding Bearer header.
```

Stop rule: if a component cannot be justified by one of these observable needs, remove it. If a gate fails, record the responsible boundary before adding machinery.

Explicitly forbidden as first-response fixes: Infisical, another vault, a persistent broker daemon, an external relay, a generic forward proxy, a tunnel, a second secret store, or plaintext bootstrap material.

## Minimal architecture

One Script-side Python process owns both synthetic endpoints:

```text
                         one Script process
                       +---------------------+
JSON connection ------>| /ingest             |
 managed secret         |   Basic             |
 injected as Basic      |     -> token in RAM |
                       |          |           |
                       |          v env only  |
                       |       mcporter       |
                       |          | Bearer    |
                       |          v           |
                       | /mcp                |
                       | compare in RAM       |
                       +----------+----------+
                                  |
                                  v
                             safe receipt
```

The same process can implement `/ingest` and the minimal fake MCP HTTP endpoint. A second fake-server process is not justified for the pilot.

## Acceptance orchestration

The pilot harness, not the Script process, orchestrates the two connection calls:

```text
1. harness starts the Script Connection query in the background
   -> processor binds its one-shot HTTP listener

2. harness invokes the JSON connection query
   -> JSON runner sends configured Basic auth to /ingest

3. processor captures only the Basic password in RAM

4. processor starts mcporter as a child process
   -> token supplied only through child environment
   -> mcporter HTTP config contains only a symbolic env reference

5. mcporter performs a minimal MCP call against /mcp
   -> /mcp verifies Bearer token equals the Basic password captured in RAM

6. processor returns a sanitized PASS/FAIL receipt and exits

7. harness performs leakage checks
```

This intentionally avoids requiring a Script-executed process to call the MarcoPolo `connection` control plane. Self-orchestration can be researched later only if a real operational use case requires it.

## Gate order

### Gate 0 — network reachability

Can the privileged JSON runner reach the listener opened by the Script execution plane?

```text
JSON runner -> Script listener
```

This is currently **UNKNOWN**. If loopback/network namespaces are isolated, STOP and record that fact. Do not introduce relay/tunnel machinery inside this pilot.

### Gate 1 — Basic capture without result materialization

The processor must receive the Authorization header, decode Basic, retain only the password in process memory, and return no credential-bearing response body.

### Gate 2 — Basic -> environment -> mcporter -> Bearer

The processor launches `mcporter` with a child-only environment variable. The mcporter definition references the variable symbolically and does not contain the value.

The fake MCP endpoint accepts the call only when the Bearer token exactly matches the password captured at Gate 1.

### Gate 3 — leakage scan

The synthetic marker must not appear in observable persistent/model-visible surfaces after the run.

## Secret boundary

Allowed transient locations:

```text
MarcoPolo managed JSON credential field
JSON executor request auth
Script process memory
mcporter child environment
mcporter outbound Authorization header
fake MCP process memory (same Script process)
```

Forbidden observable/persistent locations:

```text
Git repository
/workspace files
query files
Script query/argv
mcporter argv
persistent mcporter config
stdout/stderr
connection result payload
DuckDB relation
trace/record output
shell history
issue / PR / review text
```

No synthetic credential value is committed to this document. The acceptance harness receives only a marker name for leakage scanning through a controlled test mechanism; the real pilot must avoid teaching the repository the credential value.

## PASS contract

All must hold:

```text
json_to_script_reachable = true
basic_received           = true
mcporter_called          = true
bearer_matches_basic     = true
secret_in_workspace      = false
secret_in_result         = false
secret_in_duckdb         = false
secret_in_argv           = false   # where observable
secret_in_logs           = false
```

Receipt output should contain booleans/status only, never Authorization, Basic payloads, hashes of the secret, or decoded credential material.

## FAIL-closed rules

- listener unreachable -> STOP at Gate 0;
- missing/malformed Basic -> STOP;
- mcporter needs plaintext in argv or persistent file -> STOP;
- Bearer mismatch/absence -> STOP;
- any secret persistence/model-visible leakage -> STOP;
- no automatic fallback to relay, daemon, vault, encoded file, or alternate secret store.

## Implementation sketch, not commitment

A single small Python handler is sufficient if the gates are viable:

- standard-library threaded HTTP server or equivalent bounded listener;
- `/ingest` accepts one expected Basic-auth request;
- token held in an in-memory variable only;
- temporary mcporter config, if required, contains only `${PILOT_TOKEN}` and is created under `/tmp` then deleted;
- minimal MCP contract only: enough initialize/tool-list/tool-call behavior for one `probe` call;
- strict timeout and one-shot shutdown;
- shell mode remains off;
- no request/header debug logging.

The exact implementation should stay smaller than this design. Any new component needs an evidence-backed reason.

## Codex consultation questions

Please review this as a **pre-implementation architecture falsification**, not as an invitation to build infrastructure.

1. Is the outer acceptance harness materially simpler than making the Script process invoke `connection query` itself? Is any self-orchestration actually required to prove the transport hypothesis?
2. Is there a smaller supported mcporter path for child-env -> HTTP Authorization header that avoids even an ephemeral config file?
3. Can the one-process `/ingest` + fake `/mcp` design deadlock or accidentally force credential logging/materialization under normal mcporter behavior?
4. Does any current MarcoPolo boundary make Gate 0 impossible or misleading (for example separate network namespaces or executor hosts)?
5. Are the leakage assertions measurable with the currently exposed runtime, and which must remain `UNKNOWN` rather than be claimed clean?
6. Is any component above unjustified by the Five-Whys chain?
7. Most importantly: if a gate fails, identify the smallest responsible boundary. **Do not propose Infisical, another vault, a daemon, relay, tunnel, proxy platform, or additional secret manager unless the failure evidence makes that component strictly necessary.**

The desired review outcome is either a smaller pilot, a concrete falsification, or confirmation that this is the minimum useful experiment.
