# Azure CLI runtime

`az.sh` is an NFS-safe launcher for the pinned Microsoft Azure CLI package.

The expanded runtime is never executed from `/workspace`. The official Debian
package is kept durably under `/workspace/tools/azure-cli/runtime/`, verified
against the pinned Microsoft APT SHA-256, and materialized into a private `/tmp`
cache on demand.

The launcher owns runtime materialization only. Azure OAuth/config state is a
separate credential boundary and is not stored in the runtime package or cache
contract.

Default package:

```text
/workspace/tools/azure-cli/runtime/azure-cli_2.91.0-1~bookworm_amd64.deb
```

Usage:

```bash
/workspace/marcopolo-cookbook/azure-cli/az.sh version
```
