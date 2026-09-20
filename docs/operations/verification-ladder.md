# Cross-project verification ladder v0.1

The project should not depend on one model, reviewer, runtime, or workspace for
correctness. Use the cheapest deterministic layer that can establish the claim,
and promote recurring findings into executable checks.

## L0 — MarcoPolo interactive/local

Use MarcoPolo for the fast loop: changed-file lint, focused unit/regression tests,
small canaries, repository inspection, and interactive debugging. `tools/dev/check`
remains the preferred first endpoint when a repository provides it.

Do not install heavy dependency forests onto `/workspace` merely to reproduce a
hosted analysis job. MarcoPolo's NFS-backed workspace, network/WAF variability,
and constrained runtime make it the wrong default home for expensive full-repo
analysis. Ephemeral `/tmp` runtimes are acceptable when a local verifier truly
needs them and they are reproducible.

## L1 — GitHub Actions hosted CI

Use hosted CI for reproducible full-repository work that is too expensive or too
noisy for the interactive loop: full lint/type/security/static analysis,
compatibility matrices, network/currentness doctors, and durable receipts.

Shared cookbook workflows own runner mechanics only. Repository-local endpoints
own project semantics and tool versions. The first profiles are:

- `reusable-canonical-qa.yml`: calls the repository canonical QA endpoint;
- `reusable-heavy-python.yml`: installs a caller-owned hash-pinned analysis lock
  and calls the repository's heavy-analysis endpoint.

A repository should normally expose heavy Python policy through
`tools/ci/heavy-python` plus `requirements/ci-heavy.txt`. Which analyzers run is a
repository decision; the shared workflow must not silently add a new lint policy.

Cross-repository QA history adds four operational rules:

- checkout in read-only QA uses `persist-credentials: false`;
- an acceptance profile does not use `continue-on-error` to soften its verdict;
- a genuinely advisory witness may degrade only when that degradation is separately
  observable and does not substitute for the acceptance gate;
- long heavy analysis emits lightweight resource telemetry at no faster than a
  60-second cadence using cheap procfs/filesystem observations rather than nested
  scans or network calls.

New expensive stress cases, research smokes, or analyzers should begin outside the
ordinary blocking PR gate. Promote them into a blocking invariant only after they
demonstrate stable signal or protect a reproduced regression.

## L2 — Codespace interactive heavy debug

Use a Codespace when a heavy hosted RED needs interactive diagnosis that is
impractical in MarcoPolo. Codespace is a debugging surface, not acceptance
authority. Once the defect is understood, encode it as a deterministic regression
or check and place it permanently in L0 or L1.

## Learning loop

Classify useful findings from self-review, Codex/LLM review, forum field reports,
CI failures, or runtime incidents:

1. one-off or non-deterministic: preserve evidence only;
2. reproducible defect: add a regression;
3. recurring repository class: add a repository QA invariant;
4. recurring cross-project class: add or update a shared CI profile or cookbook
   rule.

An LLM may discover a defect class, but the durable knowledge should be executable
when practical. Codex quota or model unavailability must not erase already encoded
checks or freeze ordinary deterministic development.

## Authority and resource boundaries

- CI PASS proves only the checks that ran; it does not grant merge/release authority.
- Reusable workflows default to `contents: read` and require no secrets.
- Heavy caches and installed tools live on the hosted runner, not persistent NFS.
- No automatic external mutation belongs in a lint/analysis profile.
- Project-specific write/readback or scientific acceptance remains a separate gate.
- Artifact-producing CI should use a separate producer -> fresh consumer -> receipt
  pattern when acceptance depends on artifact portability; ordinary lint templates
  should not inherit that cost by default.
