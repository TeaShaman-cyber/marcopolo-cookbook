from pathlib import Path
import tempfile
import unittest

from tools.context_router import (
    ContextRoutingError,
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


if __name__ == "__main__":
    unittest.main()
