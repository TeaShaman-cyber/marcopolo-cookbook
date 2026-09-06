import json
import tempfile
import unittest
from pathlib import Path

from tools.context_router import (
    ContextRoutingError,
    compile_context,
    extract_section,
    load_manifest,
    resolve_route_chain,
    select_route,
    validate_manifest,
)

SCHEMA = "cookbook-routing-v0.1"


def route(route_id="x", **overrides):
    value = {
        "id": route_id,
        "priority": 1,
        "match": {},
        "inherits": [],
        "inhibits": [],
        "sections": [],
    }
    value.update(overrides)
    return value


def manifest(routes):
    return {
        "schema_version": SCHEMA,
        "defaults": {"max_sections": 4, "fallback_route": "default.unknown"},
        "routes": [route("default.unknown", priority=-1000), *routes],
    }


class ContextRouterLoadTest(unittest.TestCase):
    def test_non_object_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "routes.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ContextRoutingError, "MANIFEST_INVALID"):
                load_manifest(path)


class ContextRouterManifestTest(unittest.TestCase):
    def test_invalid_schema_version_is_rejected(self):
        value = manifest([])
        value["schema_version"] = "wrong"
        with self.assertRaisesRegex(ContextRoutingError, "SCHEMA_VERSION_INVALID"):
            validate_manifest(value, Path.cwd())

    def test_duplicate_route_id_is_rejected(self):
        with self.assertRaisesRegex(ContextRoutingError, "ROUTE_ID_DUPLICATE"):
            validate_manifest(
                manifest([route("x"), route("x", priority=2)]), Path.cwd()
            )

    def test_invalid_label_key_is_rejected(self):
        value = manifest([route("x", match={"Bad Key": ["value"]})])
        with self.assertRaisesRegex(ContextRoutingError, "LABEL_KEY_INVALID"):
            validate_manifest(value, Path.cwd())

    def test_missing_inheritance_target_is_rejected(self):
        value = manifest([route("x", inherits=["missing"])])
        with self.assertRaisesRegex(ContextRoutingError, "INHERIT_TARGET_MISSING"):
            validate_manifest(value, Path.cwd())

    def test_missing_inhibition_target_is_rejected(self):
        value = manifest([route("x", inhibits=["missing"])])
        with self.assertRaisesRegex(ContextRoutingError, "INHIBIT_TARGET_MISSING"):
            validate_manifest(value, Path.cwd())

    def test_inheritance_cycle_is_rejected(self):
        value = manifest([route("a", inherits=["b"]), route("b", inherits=["a"])])
        with self.assertRaisesRegex(ContextRoutingError, "INHERITANCE_CYCLE"):
            validate_manifest(value, Path.cwd())

    def test_duplicate_section_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text("## A\nbody\n", encoding="utf-8")
            ref = {"path": "doc.md", "heading": "## A"}
            value = manifest([route("x", sections=[ref, dict(ref)])])
            with self.assertRaisesRegex(ContextRoutingError, "SECTION_DUPLICATE"):
                validate_manifest(value, root)

    def test_section_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            root.mkdir()
            outside = Path(td) / "outside.md"
            outside.write_text("## A\nbody\n", encoding="utf-8")
            escape_path = ".." + "/outside.md"
            value = manifest(
                [route("x", sections=[{"path": escape_path, "heading": "## A"}])]
            )
            with self.assertRaisesRegex(ContextRoutingError, "SECTION_PATH_ESCAPE"):
                validate_manifest(value, root)

    def test_missing_section_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            value = manifest(
                [route("x", sections=[{"path": "missing.md", "heading": "## A"}])]
            )
            with self.assertRaisesRegex(ContextRoutingError, "SECTION_FILE_MISSING"):
                validate_manifest(value, root)

    def test_missing_heading_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text("## B\nbody\n", encoding="utf-8")
            value = manifest(
                [route("x", sections=[{"path": "doc.md", "heading": "## A"}])]
            )
            with self.assertRaisesRegex(ContextRoutingError, "SECTION_HEADING_MISSING"):
                validate_manifest(value, root)

    def test_ambiguous_heading_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text("## A\none\n## A\ntwo\n", encoding="utf-8")
            value = manifest(
                [route("x", sections=[{"path": "doc.md", "heading": "## A"}])]
            )
            with self.assertRaisesRegex(
                ContextRoutingError, "SECTION_HEADING_AMBIGUOUS"
            ):
                validate_manifest(value, root)

    def test_valid_minimal_manifest_passes(self):
        validate_manifest(manifest([]), Path.cwd())


class ContextRouterSelectionTest(unittest.TestCase):
    def test_match_keys_are_and_and_values_are_or(self):
        value = manifest(
            [
                route(
                    "a",
                    priority=10,
                    match={
                        "surface": ["workspace_shell"],
                        "operation": ["structured_edit", "generated_file"],
                    },
                ),
                route("b", priority=5, match={"surface": ["workspace_shell"]}),
            ]
        )
        self.assertEqual(
            select_route(
                value, {"surface": "workspace_shell", "operation": "structured_edit"}
            ),
            "a",
        )

    def test_absent_label_does_not_match(self):
        value = manifest(
            [route("a", priority=10, match={"operation": ["structured_edit"]})]
        )
        self.assertIsNone(select_route(value, {"surface": "workspace_shell"}))

    def test_fallback_is_not_a_normal_candidate(self):
        self.assertIsNone(select_route(manifest([]), {}))

    def test_inhibited_matching_route_is_removed(self):
        value = manifest(
            [
                route(
                    "unsafe",
                    priority=100,
                    match={"domain": ["github"], "operation": ["mutation"]},
                ),
                route(
                    "governed",
                    priority=50,
                    match={"domain": ["github"], "operation": ["mutation"]},
                    inhibits=["unsafe"],
                ),
            ]
        )
        self.assertEqual(
            select_route(value, {"domain": "github", "operation": "mutation"}),
            "governed",
        )

    def test_equal_priority_survivors_fail(self):
        value = manifest(
            [
                route("a", priority=10, match={"surface": ["workspace_shell"]}),
                route("b", priority=10, match={"surface": ["workspace_shell"]}),
            ]
        )
        with self.assertRaisesRegex(ContextRoutingError, "ROUTE_AMBIGUOUS"):
            select_route(value, {"surface": "workspace_shell"})

    def test_inheritance_chain_is_root_to_leaf_and_deduplicated(self):
        value = manifest(
            [
                route("root"),
                route("shared", inherits=["root"]),
                route("left", inherits=["shared"]),
                route("right", inherits=["root"]),
                route("winner", inherits=["left", "right"]),
            ]
        )
        self.assertEqual(
            resolve_route_chain(value, "winner"),
            ["root", "shared", "left", "right", "winner"],
        )


class ContextRouterCompileTest(unittest.TestCase):
    def test_extract_section_includes_children_and_stops_at_peer(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text(
                "# Root\nintro\n\n## A\nalpha\n\n### A child\nchild\n\n## B\nbeta\n",
                encoding="utf-8",
            )
            section = extract_section(root, {"path": "doc.md", "heading": "## A"})
            self.assertEqual(section["path"], "doc.md")
            self.assertEqual(section["heading"], "## A")
            self.assertIn("### A child\nchild", section["content"])
            self.assertNotIn("## B", section["content"])

    def test_extract_section_preserves_utf8(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text("## Чай\nпривет ☕\n", encoding="utf-8")
            section = extract_section(root, {"path": "doc.md", "heading": "## Чай"})
            self.assertIn("привет ☕", section["content"])

    def test_extract_section_rejects_missing_heading(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text("## B\nbeta\n", encoding="utf-8")
            with self.assertRaisesRegex(ContextRoutingError, "SECTION_HEADING_MISSING"):
                extract_section(root, {"path": "doc.md", "heading": "## A"})

    def test_extract_section_rejects_ambiguous_heading(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text("## A\none\n## A\ntwo\n", encoding="utf-8")
            with self.assertRaisesRegex(
                ContextRoutingError, "SECTION_HEADING_AMBIGUOUS"
            ):
                extract_section(root, {"path": "doc.md", "heading": "## A"})

    def test_compile_context_emits_matched_packet(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text("## A\nalpha\n", encoding="utf-8")
            value = manifest(
                [
                    route(
                        "workspace-shell.structured-edit",
                        priority=10,
                        match={
                            "surface": ["workspace_shell"],
                            "operation": ["structured_edit"],
                        },
                        sections=[{"path": "doc.md", "heading": "## A"}],
                    )
                ]
            )
            packet = compile_context(
                value,
                {"operation": "structured_edit", "surface": "workspace_shell"},
                root,
            )
            self.assertEqual(packet["schema_version"], "cookbook-context-v0.1")
            self.assertEqual(packet["route_state"], "MATCHED")
            self.assertEqual(packet["route_id"], "workspace-shell.structured-edit")
            self.assertEqual(
                packet["labels"],
                {"operation": "structured_edit", "surface": "workspace_shell"},
            )
            self.assertEqual(
                [(s["path"], s["heading"]) for s in packet["sections"]],
                [("doc.md", "## A")],
            )

    def test_compile_context_emits_unknown_packet(self):
        packet = compile_context(manifest([]), {"domain": "unclassified"}, Path.cwd())
        self.assertEqual(
            packet,
            {
                "schema_version": "cookbook-context-v0.1",
                "route_state": "UNKNOWN",
                "route_id": "default.unknown",
                "labels": {"domain": "unclassified"},
                "sections": [],
            },
        )

    def test_compile_context_rejects_budget_overflow_before_partial_packet(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text("## A\na\n## B\nb\n", encoding="utf-8")
            value = manifest(
                [
                    route("parent", sections=[{"path": "doc.md", "heading": "## A"}]),
                    route(
                        "winner",
                        priority=10,
                        match={"surface": ["workspace_shell"]},
                        inherits=["parent"],
                        sections=[{"path": "doc.md", "heading": "## B"}],
                    ),
                ]
            )
            value["defaults"]["max_sections"] = 1
            with self.assertRaisesRegex(ContextRoutingError, "CONTEXT_BUDGET_EXCEEDED"):
                compile_context(value, {"surface": "workspace_shell"}, root)

    def test_fixture_cases(self):
        fixture_path = Path("tests/fixtures/context-routing-v0.1.json")
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for path, content in fixture["documents"].items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            value = fixture["manifest"]
            validate_manifest(value, root)
            for case in fixture["cases"]:
                if "expected_error" in case:
                    with self.assertRaisesRegex(
                        ContextRoutingError, case["expected_error"]
                    ):
                        compile_context(value, case["labels"], root)
                    continue
                packet = compile_context(value, case["labels"], root)
                self.assertEqual(
                    packet["route_state"], case["route_state"], case["name"]
                )
                self.assertEqual(packet["route_id"], case["route_id"], case["name"])
                self.assertEqual(
                    [s["heading"] for s in packet["sections"]],
                    case["headings"],
                    case["name"],
                )


if __name__ == "__main__":
    unittest.main()
