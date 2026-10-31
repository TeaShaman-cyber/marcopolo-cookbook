import json
import unittest
from pathlib import Path


class MarcoPoloCoreRouterPluginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.plugin_root = cls.root / "plugins" / "marcopolo-core-router"
        cls.manifest_path = cls.plugin_root / "plugin.json"
        cls.skill_path = (
            cls.plugin_root / "skills" / "marcopolo-core-router" / "SKILL.md"
        )

    def test_manifest_is_portable_plugin_v023(self):
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["$schema"],
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        )
        self.assertEqual(manifest["name"], "marcopolo-core-router")
        self.assertEqual(manifest["version"], "0.2.3")
        interface = manifest["extensions"]["com.openai"]["interface"]
        self.assertEqual(interface["displayName"], "MarcoPolo Core Router")
        self.assertLessEqual(len(interface["shortDescription"]), 30)
        self.assertEqual(interface["category"], "Productivity")

    def test_skill_is_thin_and_has_required_guardrails(self):
        text = self.skill_path.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 120)
        self.assertRegex(text, r"(?m)^name: marcopolo-core-router$")
        self.assertRegex(text, r"(?m)^description: .+")
        self.assertIn("credentialed connection setup", text)
        for required in (
            "403",
            "capability != permission",
            "/workspace/RULES.md",
            "exact remote readback",
            "observable postcondition",
            "DEGRADED",
            "UNKNOWN",
            "coordination projection",
            "narrowest owning",
            "reverse issue/PR projectItems",
            "visibility != existence",
            "appropriate authorized profile",
            "## Cross-runtime file bridge",
            "prefer Google Drive as the standard bridge",
            "use base64 chunking only after",
            "## Managed credential connections",
            "connection_setup",
            "privileged credential boundary",
            "arbitrary local subprocess",
            "model-visible plaintext",
        ):
            self.assertIn(required, text)

    def test_skill_routes_detail_instead_of_copying_the_cookbook(self):
        text = self.skill_path.read_text(encoding="utf-8")
        self.assertIn("smallest relevant section", text)
        self.assertIn("marcopolo/README.md", text)
        self.assertNotIn("dump entire cookbook", text.lower())


if __name__ == "__main__":
    unittest.main()
