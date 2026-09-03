# Cloud-reference field notes

## Connector-level payload-shape canary

The MarcoPolo control-plane filter is outside the persistent workspace runtime. A script running inside `/workspace` cannot directly observe whether a future `workspace_shell` request is rejected before execution.

`cloud-reference/bin/payload-shape-canary` therefore emits a reviewed corpus of harmless, semantically equivalent commands. The outer connector/harness must execute each case as a separate `workspace_shell` request and record only:

- case id;
- connector accepted/blocked;
- target command executed yes/no;
- stdout hash or tiny constant result;
- observation timestamp.

Allowed classifications are `NO_DIFFERENCE_OBSERVED`, `PAYLOAD_SHAPE_SENSITIVE_CONTROL_PLANE_FILTERING`, and `INCONCLUSIVE`. A blocked case is not retried after sufficient evidence exists, and this mechanism is never used to transform security-sensitive content.
