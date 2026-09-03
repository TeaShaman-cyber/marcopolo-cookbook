# MarcoPolo Cloud Reference and Hosting Evidence Design

## Status

Approved in chat on 2026-09-03 for specification. Implementation remains gated on review of this written design.

## Goal

Add a small, reproducible cloud-reference layer to `marcopolo-cookbook` that can passively characterize the hosting/control-plane surface of MarcoPolo endpoints, query reviewed anonymous MCP reference sources for provider-specific documentation, and emit machine-readable evidence receipts without attempting to bypass WAF, authentication, or provider safety controls.

## Scope

This subsystem is for reference and diagnostics only.

It may:

- collect passive DNS, CNAME, IP/ASN, TLS, HTTP-header, and error-page evidence for explicitly named public endpoints;
- query approved anonymous MCP/reference services for cloud-provider, hosting, MCP, and WAF documentation;
- compare independent evidence sources and classify provider confidence;
- preserve raw hashes plus compact derived receipts;
- distinguish target failure from connector/control-plane failure;
- create reusable `mcporter` wrappers for bounded reference queries;
- publish sanitized findings to the appropriate public research issues.

It must not:

- evade or weaken WAF, provider safety, authentication, authorization, rate limits, or other controls;
- mutate MarcoPolo routing based on an unreviewed provider guess;
- attach newly discovered MCP servers automatically;
- expose credentials, tokens, private payloads, or sensitive runtime data;
- treat a registry description as live capability evidence;
- treat a single HTTP header, IP, ASN, CNAME, or error-page signature as conclusive hosting authority.

## Repository placement

The implementation lives inside `TeaShaman-cyber/marcopolo-cookbook` under the existing `mcporter`/field-notes discipline.

Proposed layout:

```text
cloud-reference/
├── README.md
├── bin/
│   ├── hosting-identify
│   ├── cloud-docs
│   ├── waf-reference
│   └── mcp-registry-check
├── queries/
│   └── reviewed-sources.json
├── schemas/
│   └── evidence-receipt.schema.json
└── tests/
    └── acceptance.sh

docs/
├── field-notes/
│   └── cloud-reference.md
└── research/
    └── hosting-evidence/
```

No raw trace directory is committed. Raw temporary observations may exist locally during a probe but only sanitized derived receipts and explicit safe hashes are eligible for publication.

## Component boundaries

### 1. `hosting-identify`

Purpose: collect passive infrastructure evidence for one explicit public hostname.

Inputs:

- hostname;
- optional observation label;
- optional timeout bounded by the wrapper.

Evidence classes:

- DNS A/AAAA answers;
- CNAME chain;
- resolved IPs;
- ASN/network-owner metadata when available through an approved source;
- TLS certificate issuer/SAN metadata;
- HTTP status and selected non-sensitive headers;
- stable hashes of bounded error-page bodies when a request returns an error;
- observable intermediary/provider markers.

The wrapper must preserve uncertainty. It returns observations, not a provider verdict by itself.

### 2. `cloud-docs`

Purpose: query reviewed reference MCPs for official cloud/provider documentation related to an observed feature.

Typical sources may include currently verified anonymous services such as:

- AWS Knowledge MCP for AWS-specific documentation;
- Cloudflare Docs MCP for Cloudflare-specific documentation;
- Microsoft Learn MCP where Microsoft/Azure documentation is relevant;
- Context7 or another reviewed documentation source when provider documentation is available there.

Source availability is runtime evidence and must be rechecked. This list is not authorization to trust or activate any future endpoint with a matching name.

### 3. `waf-reference`

Purpose: retrieve provider-specific documentation explaining public WAF/security-filter behavior and diagnostic signals.

The wrapper is explicitly defensive/reference-only. Queries describe observed failures, status codes, documented control-plane behavior, and false-positive diagnostics. It must not ask for payload transformations intended to bypass filtering.

### 4. `mcp-registry-check`

Purpose: query independent registries/watchers about a candidate reference MCP before any use.

Preferred federation:

```text
HAPI MCP Registry
      +
RMCP
      +
Not Human Search
      +
FreeAPI.watch
      ↓
registry/reference evidence
      ↓
independent live initialize/tools-list when appropriate
```

A registry hit is discovery evidence only. Anonymous execution requires a bounded tool-call canary where the service class permits it.

## Evidence receipt

All wrappers emit JSON. The common receipt envelope is:

```json
{
  "schema_version": 1,
  "target": "mcp.marcopolo.dev",
  "observation_time": "RFC3339 timestamp",
  "probe_kind": "hosting-identify | cloud-docs | waf-reference | mcp-registry-check",
  "observations": [],
  "reference_sources": [],
  "provider_candidates": [],
  "classification": "VERIFIED_PROVIDER | LIKELY_PROVIDER | MULTI_PROVIDER_OR_PROXY | INSUFFICIENT_EVIDENCE",
  "confidence": 0.0,
  "raw_hashes": [],
  "failure": null
}
```

### Provider classification semantics

`VERIFIED_PROVIDER`
: Multiple independent evidence classes converge and at least one high-authority provider-owned signal directly identifies the serving/control-plane provider. Use sparingly.

`LIKELY_PROVIDER`
: Multiple independent signals converge, but no direct provider-owned authority closes the attribution.

`MULTI_PROVIDER_OR_PROXY`
: Evidence indicates multiple layers, such as DNS/CDN/proxy/service-hosting boundaries, or signals materially disagree.

`INSUFFICIENT_EVIDENCE`
: Evidence is missing, weak, contradictory, or the observation path failed before attribution was possible.

A numeric `confidence` supplements but never overrides the categorical evidence record.

## Failure taxonomy

The wrappers preserve failed observation layers explicitly.

```text
TARGET_HTTP_ERROR
TARGET_DNS_ERROR
TARGET_TLS_ERROR
REFERENCE_SOURCE_ERROR
REFERENCE_AUTH_REQUIRED
REFERENCE_PROTOCOL_DRIFT
CONNECTOR_CONTROL_PLANE_BLOCKED
LOCAL_RUNTIME_ERROR
INCONCLUSIVE
```

Important invariants:

```text
search miss                  != absence
registry metadata            != live capability
connector 403                != target 403
connector timeout            != target timeout
HTTP header                  != provider authority
ASN owner                    != application hosting authority
CNAME                        != complete request path
error-page resemblance       != verified WAF identity
```

## Payload-shape investigation boundary

The existing MarcoPolo 403 investigation may use benign A/B observations to determine whether connector/control-plane filtering is sensitive to serialized request shape.

Allowed experiment:

- same harmless semantic operation;
- equivalent representations with different quoting/command decomposition;
- no secrets;
- no exploit strings;
- no attempts to evade a confirmed security decision;
- stop after enough evidence exists to classify the observation.

The finding may be recorded as `PAYLOAD_SHAPE_SENSITIVE_CONTROL_PLANE_FILTERING` only when an equivalent harmless operation reproducibly differs by representation. This label describes observed behavior; it does not claim knowledge of the provider's internal WAF implementation.

## Reference-source authorization

A source moves through explicit states:

```text
DISCOVERED
  ↓
LIVE_METADATA_VERIFIED
  ↓
ANONYMOUS_EXECUTION_VERIFIED
  ↓
REVIEWED_REFERENCE_SOURCE
```

Only `REVIEWED_REFERENCE_SOURCE` endpoints enter the wrapper configuration.

Authentication-required services may be recorded as evidence but are not silently used by these anonymous-reference wrappers.

## Issue routing

Findings are published according to authority boundary rather than convenience.

- `theseus-public-observatory#4` — discovery, live health, anonymous MCP capability, registry contradictions.
- `theseus-public-observatory#6` — free/cloud-adjacent reference, data, compute, and hosting-discovery surfaces.
- `marcopolo-cookbook` issues — MarcoPolo-specific hosting evidence, 403/control-plane taxonomy, payload-shape observations, wrapper behavior, and reusable field notes.
- `theseus-public-observatory#5` — only later, if reviewed evidence becomes an authorized Hermes routing/reference capability.
- `theseus-needle-lab` — no routing from this subsystem; Needle remains out of scope.

Upstream provider/plugin issues may be opened only after a minimal reproducible observation is preserved publicly and independently read back.

## Initial research target

The first target is the public MarcoPolo connector endpoint already observed in this work:

```text
mcp.marcopolo.dev
```

The first pass is passive only:

1. DNS/CNAME resolution.
2. IP/network-owner evidence.
3. TLS certificate metadata.
4. bounded HTTP response/status/header observations.
5. comparison of successful and pre-execution 403 observations already present in field notes/session history.
6. provider candidate classification.
7. provider-specific documentation lookup using reviewed reference MCPs.
8. sanitized receipt and issue update.

No active WAF bypass testing is part of this pass.

## Testing and acceptance

The implementation is accepted when all of the following hold:

1. Every wrapper has a deterministic CLI interface and emits JSON on stdout.
2. Invalid input produces a typed non-zero failure without ambiguous partial success.
3. At least two independent evidence classes are required before `LIKELY_PROVIDER` is possible.
4. `VERIFIED_PROVIDER` cannot be produced solely from heuristic signatures.
5. Connector/control-plane errors remain distinct from target errors.
6. At least two reviewed anonymous reference MCPs are exercised through bounded canaries.
7. `hosting-identify mcp.marcopolo.dev` produces a sanitized receipt with raw hashes and explicit uncertainty.
8. A benign payload-shape A/B can be recorded without bypass behavior and without secrets.
9. Acceptance tests run with one command and require no interactive prompts.
10. Generated outputs, raw traces, credentials, and runtime caches remain excluded from Git.

## Security and publication rules

- No credentials or authorization headers are logged or committed.
- Public receipts include only information already observable from public endpoints or public documentation.
- Body capture is bounded; publication prefers stable hashes plus tiny diagnostic excerpts only when safe and necessary.
- Provider attribution remains evidence-based and reversible when infrastructure changes.
- Historical contradictions are preserved instead of rewritten away.

## Non-goals

This design does not create a general-purpose reconnaissance framework, WAF evasion toolkit, autonomous MCP installer, production routing layer, or Hermes integration. Those would require separate explicit designs and approval.
