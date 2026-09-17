# Scientific verifier runtime

This component provides the reproducible local scientific runtime used by the formal-verifier research in `TeaShaman-cyber/theseus-research#42`. Its purpose is to remove model-mediated/manual glue between retrieval and deterministic verification, not to create a general scientific framework.

## Runtime boundary

Canonical state lives in Git under `scientific-verifier/`. Generated virtual environments never live under `/workspace`; validated runtime caches are materialized under `/tmp/marcopolo-scientific-verifier-<uid>/`.

The committed `runtime/requirements.lock`, runtime identity, scripts, tests, and receipts are authoritative. An existing `/tmp` cache is only a reproducible runtime instance and may disappear at any time.

## Materialize

```bash
scientific-verifier/scripts/install-runtime.sh
scientific-verifier/scripts/ensure-runtime.sh
```

The runtime uses Python 3.11 and the hash-pinned NumPy, NetworkX, SymPy, and SciPy dependency set from `runtime/requirements.lock`.

## Verify

```bash
scientific-verifier/tests/acceptance.sh
```

The acceptance canary validates the `/tmp` cache path, Python contract, real package imports, deterministic runtime receipt shape, bundle identity, and package-version presence.

## Scope

This slice does **not** yet provide the source-snapshot adapter, deterministic typed projection, applicability router, or held-out prediction workflow. Those remain research work after the runtime stand is accepted.

A later slice may use the existing repo-managed mcporter/Wolfram route as an independent witness. Cookbook issue #4 remains separate work for symbolic-compute fallback routing when Wolfram is unavailable.
