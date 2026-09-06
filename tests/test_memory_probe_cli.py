import unittest

from tools.memory_probe_cli import (
    PROBE_PRINCIPAL,
    PROBE_SCOPE,
    ProbeConfig,
    recall_probe,
)


class FakeAdapter:
    def __init__(self):
        self.calls = []

    def recall(self, context, *, scope, filters, limit=20, cursor=None):
        self.calls.append((context.trusted_principal_id, scope, filters, limit, cursor))
        return {"status": "HIT", "items": [{"event_id": filters["event_id"]}]}


class MemoryProbeCliTest(unittest.TestCase):
    def test_recall_probe_fixes_principal_and_scope_outside_runtime_config(self):
        config = ProbeConfig(connection_name="synthetic-pg", query_dir="/tmp/q", event_id="evt-canary")
        adapter = FakeAdapter()

        result = recall_probe(config, adapter=adapter)

        self.assertEqual(PROBE_PRINCIPAL, "synthetic-skill-probe")
        self.assertEqual(PROBE_SCOPE, "synthetic/issue-17/skill-attribution")
        self.assertEqual(
            adapter.calls,
            [(PROBE_PRINCIPAL, PROBE_SCOPE, {"event_id": "evt-canary"}, 1, None)],
        )
        self.assertEqual(result["adapter_call_receipt"]["scope"], PROBE_SCOPE)
        self.assertEqual(result["packet"]["status"], "HIT")


if __name__ == "__main__":
    unittest.main()
