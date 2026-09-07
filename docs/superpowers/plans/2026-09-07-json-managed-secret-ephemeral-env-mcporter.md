# JSON Managed Canary to mcporter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build one bounded synthetic pilot for the accepted managed-value -> Script -> child environment -> mcporter path and classify transport plus observable non-disclosure.

**Architecture:** One Script-side Python process serves the ingest endpoint and the local MCP endpoint. A workspace-side Python harness starts Script asynchronously, waits for a nonce READY marker, invokes the existing JSON connection, captures bounded evidence, and stops at the first failed gate.

**Tech Stack:** Python 3 stdlib, unittest, MarcoPolo connection CLI, existing JSON and Script connections, pinned `/workspace/tools/mcporter/bin/mcporter` runtime.

**Spec:** `docs/superpowers/specs/2026-09-07-json-managed-secret-ephemeral-env-mcporter-design.md`

## Global Constraints

- Synthetic canary only; no production provider.
- The external acceptance controller already knows the synthetic canary; the runtime harness does not receive it.
- Runtime value bytes and derived auth forms never enter Git, query text, workspace artifacts, argv, traces, or result notes.
- mcporter argv is fixed and non-sensitive; the runtime value travels only in child environment state.
- Reuse the existing pinned mcporter runtime. No npm or node_modules work on `/workspace`.
- Avoid compound quoting-heavy `workspace_shell` payloads. A control-plane 403 is not a target failure.
- Script shell mode stays off.
- One failed gate stops the pilot. No relay, tunnel, vault, daemon, proxy, or second store.
- Phase 1 reports only transport and observable non-disclosure; inaccessible platform surfaces remain UNKNOWN.

## Files

- Create `experiments/json-secret-env-pilot/pilot_auth_pipe.py` — one-shot handler, READY marker, child launch, minimal MCP endpoint, safe receipt.
- Create `experiments/json-secret-env-pilot/mcporter.json` — static non-sensitive server definition using the symbolic `PILOT_TOKEN` environment reference.
- Create `experiments/json-secret-env-pilot/pilot_harness.py` — workspace orchestration and bounded evidence collection.
- Create `tests/test_json_secret_env_pilot.py` — unit and local integration tests.
- Modify the accepted spec with the synthetic-controller clarification.

### Task 1: Process contract

- [ ] Write failing tests for `parse_basic_header(value)`, `build_mcporter_argv(config_path)`, and `safe_receipt(state)`.
- [ ] Verify RED with `python3 -m unittest tests.test_json_secret_env_pilot -v`.
- [ ] Implement `parse_basic_header` using validated Base64 decode and a single username/value split; malformed input raises `BASIC_MISSING_OR_MALFORMED`.
- [ ] Make `build_mcporter_argv` return exactly `("/workspace/tools/mcporter/bin/mcporter", "--config", config_path, "call", "pilot.probe")`.
- [ ] Test that a synthetic test value never appears in argv.
- [ ] Make `safe_receipt` accept only the approved boolean fields from the spec.
- [ ] Run focused tests; commit `test: lock json secret env pilot process contract`.

### Task 2: One-shot handler

- [ ] Write RED localhost tests using `http.client`: malformed ingest -> 401; first valid ingest -> 204; second ingest -> 409; MCP before ingest -> 409; wrong auth -> 401; matching auth -> probe success.
- [ ] Implement `PilotState` with booleans plus the transient runtime value held only in process memory.
- [ ] Implement `BaseHTTPRequestHandler` with `log_message()` disabled.
- [ ] Implement only MCP methods `initialize`, `notifications/initialized`, `tools/list`, and `tools/call`; expose exactly one tool named `probe`; return only non-sensitive text `ok`.
- [ ] After successful bind, atomically create `/workspace/artifacts/json-secret-env-pilot/ready-<nonce>` containing `READY`.
- [ ] Run tests; commit `feat: add one-shot auth pipe handler`.

### Task 3: Real mcporter child-env integration

- [ ] Add `mcporter.json` for `http://127.0.0.1:18765/mcp` with a symbolic `PILOT_TOKEN` header reference only. If mcporter serializes HTTP servers differently, create the equivalent through `mcporter config add` and commit only that non-sensitive serialization.
- [ ] Write a RED integration test that starts the local handler and invokes the real pinned wrapper.
- [ ] Implement `spawn_mcporter(value, config_path)` using `env = os.environ.copy()` plus one child-only `PILOT_TOKEN`; never mutate global environment.
- [ ] Assert wrapper return code 0, `mcporter_called=True`, `bearer_matches_basic=True`, and no synthetic test value in captured output.
- [ ] Run `/workspace/tools/mcporter/bin/mcporter --version`; expect 0.13.8; do not install or upgrade anything.
- [ ] Commit `feat: pass managed value through mcporter child env`.

### Task 4: Workspace acceptance harness

- [ ] Write RED tests with mocked subprocesses for staging, READY timeout, JSON failure, and cleanup.
- [ ] Copy the versioned handler to `/workspace/scripts/pilot-auth-pipe.py` and verify source/destination SHA-256 before execution.
- [ ] Generate a Script query containing only `pilot-auth-pipe.py <nonce>`.
- [ ] Generate a JSON query containing only `{"url":"http://127.0.0.1:18765/ingest"}`.
- [ ] Start Script with `subprocess.Popen([...])`; never use shell composition.
- [ ] Poll the exact READY marker for at most 10 seconds, then invoke JSON with `subprocess.run([...], timeout=20)`.
- [ ] If localhost is not shared across the JSON and Script execution planes, classify `JSON_TO_SCRIPT_UNREACHABLE` and stop without adding infrastructure.
- [ ] Return only safe status plus bounded observable surfaces needed by the external controller. The runtime harness stays canary-blind.
- [ ] Run tests; commit `feat: add bounded json secret env acceptance harness`.

### Task 5: Live synthetic acceptance

- [ ] Append to the spec that the Phase-1 canary is known to the external acceptance controller because it was generated for this experiment; the runtime harness does not receive it, and Phase 1 makes no model-blind production-secret claim.
- [ ] Run `python3 -m unittest discover -s tests -v` and `git diff --check`.
- [ ] Run once: `python3 experiments/json-secret-env-pilot/pilot_harness.py --script-connection script-hello-20260907-1314 --json-connection json-keychain-smoke-20260905-1238`.
- [ ] Stop on the first design failure code. Do not create a fallback route.
- [ ] In external controller memory only, compare bounded evidence with the already-known synthetic representations. Do not send those signatures back into MarcoPolo commands or files.
- [ ] On success record only `transport = PASS`, `observable_non_disclosure = PASS`, and the four platform-internal UNKNOWN fields from the spec.
- [ ] Commit non-sensitive evidence and push `impl/json-secret-env-pilot`.

## Self-Review

Spec gates map to Tasks 1-5; no `/scan` endpoint or architecture expansion was introduced. The runtime harness remains canary-blind. WAF/NFS rules are explicit operating constraints. Interfaces and failure boundaries are consistent with the accepted spec.