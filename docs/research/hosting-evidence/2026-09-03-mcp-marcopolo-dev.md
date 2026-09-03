# `mcp.marcopolo.dev` passive hosting evidence — 2026-09-03

## Result

Observed public serving/network provider classification: **`VERIFIED_PROVIDER: AWS`**, confidence `0.8` under the cloud-reference evidence rules.

This is scoped to the public serving/network layer. It does **not** claim that every MarcoPolo component, database, worker, or policy/filtering layer runs directly on EC2.

## Passive observations

At observation time `2026-09-03T10:18:18Z`, `mcp.marcopolo.dev` resolved to `44.226.16.168, 52.24.134.40`.

AWS provider-owned `ip-ranges.json` (`createDate: 2026-09-03-07-47-05`) placed those addresses in `us-west-2` ranges `44.224.0.0/11, 52.24.0.0/14` with matching `AMAZON` and `EC2` service entries.

TLS independently presented an Amazon-issued certificate (`Amazon RSA 2048 M04`) for `*.marcopolo.dev`.

A bounded unauthenticated HTTPS request reached the application surface and returned HTTP `401`. The selected public `server` header was `uvicorn`. The published receipt stores only a bounded body hash; transient body excerpts and correlation identifiers are excluded.

## Independent provider documentation

The reviewed anonymous AWS Knowledge MCP was exercised through the repo-local `mcporter` wrapper. Its provider-owned documentation result states that `https://ip-ranges.amazonaws.com/ip-ranges.json` is generated from AWS's internal system of record and is authoritative for AWS public IP ranges.

A second defensive AWS documentation query returned official troubleshooting material that explicitly includes AWS WAF rule misconfiguration as one possible cause of HTTP 403 responses. This is reference material only: **no current evidence attributes MarcoPolo's historical pre-execution connector 403 responses to AWS WAF.**

## Layer interpretation

```text
public DNS / addresses
        ↓
AWS-owned EC2 ranges, us-west-2
        ↓
Amazon-issued TLS certificate
        ↓
HTTPS application surface: uvicorn / 401
        ↓
internal MarcoPolo topology and connector filtering: unknown
```

Verified: the currently observed public addresses sit in AWS EC2 ranges in `us-west-2`; TLS provides an independent Amazon marker; the public application surface is reachable.

Unknown: exact AWS product topology, load-balancing/container boundary, persistence location, internal worker placement, and which upstream/provider layer produced historical connector-control-plane 403 responses.

## Controlled payload-shape canary

Five harmless semantically equivalent connector requests were executed independently through `workspace_shell`:

1. literal POSIX `printf`;
2. shell-variable `printf`;
3. Python `print`;
4. quoted heredoc;
5. compound shell sequence with `set -eu`.

All five were accepted and returned exactly `cloudref-canary`.

Controlled classification: **`NO_DIFFERENCE_OBSERVED`**.

Historical long compound requests have sometimes been rejected by the MarcoPolo connector with an HTML 403 before shell execution while nearby shorter authorized requests succeeded. Those incidents remain **`CONNECTOR_CONTROL_PLANE_BLOCKED`** evidence and motivate the payload-shape hypothesis, but the current controlled corpus does not identify a triggering token sequence and does not satisfy the spec threshold for `PAYLOAD_SHAPE_SENSITIVE_CONTROL_PLANE_FILTERING`.

## Wrapper lessons

The first `waf-reference` attempt falsely rejected the safe phrase `not bypass` because its safety filter matched the word `bypass` without considering explicit negation. A regression test now permits only explicit non-bypass phrases while continuing to reject affirmative bypass/evasion intent.

A publication-prep command also demonstrated why evidence pipelines use `set -eu`: a missing temporary receipt file otherwise allowed later commands to continue against an older untracked receipt. The final published receipt was regenerated atomically from a fresh live probe.

## Published receipt

`cloud-reference/receipts/2026-09-03-mcp-marcopolo-dev.json`

SHA256: `fe3f9caedd760fa19d372cbd269d9ac1ee27c2d948369b890be05657d423711e`
