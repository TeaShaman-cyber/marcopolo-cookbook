# Cloud Reference

Passive diagnostics and reviewed reference wrappers for public cloud/control-plane evidence. This layer does not bypass WAF, authentication, authorization, or rate limits.

Initial CLI:

```sh
cloud-reference/bin/hosting-identify mcp.marcopolo.dev
```

## Reviewed reference wrappers

```sh
cloud-reference/bin/mcp-registry-check aws-knowledge
cloud-reference/bin/cloud-docs aws 'public EC2 IP ranges and region attribution'
cloud-reference/bin/waf-reference cloudflare 'documented causes of false-positive 403 responses'
```

Wrappers build a temporary `mcporter` configuration only from `queries/reviewed-sources.json`; discovered servers are never silently attached to the global workbench.

## Acceptance

```sh
cloud-reference/tests/acceptance.sh
```
