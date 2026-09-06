from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.memory_adapter import (
    ConnectionQueryRunner,
    MemoryAdapter,
    TrustedExecutionContext,
)

PROBE_PRINCIPAL = "synthetic-skill-probe"
PROBE_SCOPE = "synthetic/issue-17/skill-attribution"
DEFAULT_CONFIG_PATH = Path("/workspace/.config/theseus-memory-attribution-probe.json")


@dataclass(frozen=True)
class ProbeConfig:
    connection_name: str
    query_dir: str
    event_id: str

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> "ProbeConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            connection_name=str(data["connection_name"]),
            query_dir=str(data["query_dir"]),
            event_id=str(data["event_id"]),
        )


def build_adapter(config: ProbeConfig) -> MemoryAdapter:
    runner = ConnectionQueryRunner(
        connection_name=config.connection_name,
        query_dir=config.query_dir,
    )
    authorization = {
        "principals": {
            PROBE_PRINCIPAL: {
                "allowed_scopes": [PROBE_SCOPE],
            }
        }
    }
    return MemoryAdapter(
        runner=runner,
        authorization=authorization,
        synthetic_only=True,
    )


def recall_probe(config: ProbeConfig, *, adapter: Any | None = None) -> dict[str, Any]:
    active_adapter = adapter if adapter is not None else build_adapter(config)
    context = TrustedExecutionContext(trusted_principal_id=PROBE_PRINCIPAL)
    packet = active_adapter.recall(
        context,
        scope=PROBE_SCOPE,
        filters={"event_id": config.event_id},
        limit=1,
    )
    return {
        "adapter_call_receipt": {
            "operation": "recall",
            "principal": PROBE_PRINCIPAL,
            "scope": PROBE_SCOPE,
            "event_id": config.event_id,
        },
        "packet": packet,
    }


def main() -> int:
    result = recall_probe(ProbeConfig.load())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
