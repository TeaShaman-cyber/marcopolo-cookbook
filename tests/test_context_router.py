import json
import tempfile
import unittest
from pathlib import Path

from tools.context_router import (
    ContextRoutingError,
    compile_context,
    extract_section,
    load_manifest,
    select_route,
    validate_manifest,
)

SCHEMA = "cookbook-routing-v0.1"


def section(path="doc.md", heading="## A"):
    return {"path": path, "heading": heading}


def route(route_id="x", match=None, include=None, sections=None, **extra):
    value = {
        "id": route_id,
        "match": {"kind": route_id} if match is None else match,
        "include": include or [],
        "sections": sections or [],
    }
    value.update(extra)
    return value


def manifest(routes=None, policies=None, max_sections=4):
    return {
        "schema_version": SCHEMA,
        "defaults": {"max_sections": max_sections, "fallback_route": "default.unknown"},
        "policies": policies or {},
        "routes": routes or [],
    }


class SimplifiedManifestTest(unittest.TestCase):
    def test_minimal_manifest_is_valid(self):
        validate_manifest(manifest(), Path.cwd())

    def test_route_match_must_be_nonempty_exact_strings(self):
        with self.assertRaisesRegex(ContextRoutingError, "ROUTE_MATCH_EMPTY"):
            validate_manifest(manifest([route("x", match={})]), Path.cwd())
        with self.assertRaisesRegex(ContextRoutingError, "MATCH_VALUE_INVALID"):
            validate_manifest(
                manifest([route("x", match={"surface": ["workspace_shell"]})]),
                Path.cwd(),
            )

    def test_old_routing_fields_are_rejected(self):
        for field in ("priority", "inherits", "inhibits"):
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(ContextRoutingError, "ROUTE_FIELD_UNKNOWN"),
            ):
                validate_manifest(manifest([route("x", **{field: []})]), Path.cwd())

    def test_route_include_must_reference_policy(self):
        value = manifest([route("x", include=["missing.policy"])])
        with self.assertRaisesRegex(ContextRoutingError, "POLICY_INCLUDE_MISSING"):
            validate_manifest(value, Path.cwd())

    def test_policy_is_sections_only(self):
        value = manifest(policies={"verify": {"sections": [], "inherits": ["x"]}})
        with self.assertRaisesRegex(ContextRoutingError, "POLICY_FIELD_UNKNOWN"):
            validate_manifest(value, Path.cwd())


class SimplifiedSelectionTest(unittest.TestCase):
    def test_exact_labels_select_one_route(self):
        value = manifest(
            [
                route(
                    "shell.edit",
                    match={
                        "surface": "workspace_shell",
                        "operation": "structured_edit",
                    },
                ),
                route("github.read", match={"domain": "github", "operation": "read"}),
            ]
        )
        self.assertEqual(
            select_route(
                value, {"surface": "workspace_shell", "operation": "structured_edit"}
            ),
            "shell.edit",
        )

    def test_missing_label_is_not_a_match(self):
        value = manifest(
            [
                route(
                    "shell.edit",
                    match={
                        "surface": "workspace_shell",
                        "operation": "structured_edit",
                    },
                )
            ]
        )
        self.assertIsNone(select_route(value, {"surface": "workspace_shell"}))

    def test_two_exact_matches_are_ambiguous_without_priority(self):
        value = manifest(
            [
                route("broad", match={"surface": "workspace_shell"}),
                route(
                    "specific",
                    match={
                        "surface": "workspace_shell",
                        "operation": "structured_edit",
                    },
                ),
            ]
        )
        with self.assertRaisesRegex(ContextRoutingError, "ROUTE_AMBIGUOUS"):
            select_route(
                value, {"surface": "workspace_shell", "operation": "structured_edit"}
            )


class SimplifiedCompileTest(unittest.TestCase):
    def test_policy_sections_precede_route_sections_and_deduplicate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text(
                "## Verify\ncheck\n## Shell\nedit\n", encoding="utf-8"
            )
            verify = section(heading="## Verify")
            value = manifest(
                routes=[
                    route(
                        "shell.edit",
                        match={
                            "surface": "workspace_shell",
                            "operation": "structured_edit",
                        },
                        include=["verification"],
                        sections=[verify, section(heading="## Shell")],
                    )
                ],
                policies={"verification": {"sections": [verify]}},
            )
            packet = compile_context(
                value,
                {"surface": "workspace_shell", "operation": "structured_edit"},
                root,
            )
            self.assertEqual(
                [s["heading"] for s in packet["sections"]], ["## Verify", "## Shell"]
            )

    def test_compile_validates_unselected_stale_reference(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text("## Good\nok\n", encoding="utf-8")
            value = manifest(
                [
                    route(
                        "good",
                        match={"kind": "good"},
                        sections=[section(heading="## Good")],
                    ),
                    route(
                        "stale",
                        match={"kind": "stale"},
                        sections=[section(heading="## Missing")],
                    ),
                ]
            )
            with self.assertRaisesRegex(ContextRoutingError, "SECTION_HEADING_MISSING"):
                compile_context(value, {"kind": "good"}, root)

    def test_budget_applies_after_policy_expansion(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text("## A\na\n## B\nb\n", encoding="utf-8")
            value = manifest(
                routes=[
                    route(
                        "x",
                        match={"kind": "x"},
                        include=["base"],
                        sections=[section(heading="## B")],
                    )
                ],
                policies={"base": {"sections": [section(heading="## A")]}},
                max_sections=1,
            )
            with self.assertRaisesRegex(ContextRoutingError, "CONTEXT_BUDGET_EXCEEDED"):
                compile_context(value, {"kind": "x"}, root)

    def test_unknown_is_only_for_zero_matching_routes(self):
        packet = compile_context(manifest(), {"kind": "none"}, Path.cwd())
        self.assertEqual(packet["route_state"], "UNKNOWN")
        self.assertEqual(packet["route_id"], "default.unknown")
        self.assertEqual(packet["sections"], [])


class MarkdownFenceTest(unittest.TestCase):
    def test_fenced_code_heading_does_not_truncate_section(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text(
                "## Shell\nintro\n```bash\n# bounded commands here\necho ok\n```\nafter fence\n## Next\nnext\n",
                encoding="utf-8",
            )
            result = extract_section(root, section(heading="## Shell"))
            self.assertIn("# bounded commands here", result["content"])
            self.assertIn("after fence", result["content"])
            self.assertNotIn("## Next", result["content"])

    def test_heading_like_text_inside_fence_does_not_make_reference_ambiguous(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text(
                "## A\nreal\n```markdown\n## A\nnot a heading\n```\n",
                encoding="utf-8",
            )
            value = manifest([route("x", match={"kind": "x"}, sections=[section()])])
            validate_manifest(value, root)


class PreservedSafetyTest(unittest.TestCase):
    def test_load_manifest_rejects_non_object(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "routes.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ContextRoutingError, "MANIFEST_INVALID"):
                load_manifest(path)

    def test_schema_version_and_duplicate_route_id_fail(self):
        bad = manifest()
        bad["schema_version"] = "wrong"
        with self.assertRaisesRegex(ContextRoutingError, "SCHEMA_VERSION_INVALID"):
            validate_manifest(bad, Path.cwd())
        with self.assertRaisesRegex(ContextRoutingError, "ROUTE_ID_DUPLICATE"):
            validate_manifest(
                manifest([route("x"), route("x", match={"kind": "other"})]), Path.cwd()
            )

    def test_invalid_label_key_fails(self):
        with self.assertRaisesRegex(ContextRoutingError, "LABEL_KEY_INVALID"):
            validate_manifest(
                manifest([route("x", match={"Bad Key": "x"})]), Path.cwd()
            )

    def test_section_path_escape_and_missing_file_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            root.mkdir()
            outside = Path(td) / "outside.md"
            outside.write_text("## A\nbody\n", encoding="utf-8")
            escape = ".." + "/outside.md"
            with self.assertRaisesRegex(ContextRoutingError, "SECTION_PATH_ESCAPE"):
                validate_manifest(
                    manifest([route("x", sections=[section(escape)])]), root
                )
            with self.assertRaisesRegex(ContextRoutingError, "SECTION_FILE_MISSING"):
                validate_manifest(
                    manifest([route("x", sections=[section("missing.md")])]), root
                )

    def test_duplicate_missing_and_ambiguous_headings_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "unique.md").write_text("## A\none\n", encoding="utf-8")
            duplicate = section(path="unique.md")
            with self.assertRaisesRegex(ContextRoutingError, "SECTION_DUPLICATE"):
                validate_manifest(
                    manifest([route("x", sections=[duplicate, dict(duplicate)])]), root
                )
            with self.assertRaisesRegex(ContextRoutingError, "SECTION_HEADING_MISSING"):
                validate_manifest(
                    manifest(
                        [
                            route(
                                "x",
                                sections=[
                                    section(path="unique.md", heading="## Missing")
                                ],
                            )
                        ]
                    ),
                    root,
                )
            (root / "doc.md").write_text("## A\none\n## A\ntwo\n", encoding="utf-8")
            with self.assertRaisesRegex(
                ContextRoutingError, "SECTION_HEADING_AMBIGUOUS"
            ):
                validate_manifest(manifest([route("x", sections=[section()])]), root)


class SimplifiedFixtureTest(unittest.TestCase):
    def test_fixture_cases(self):
        fixture = json.loads(
            Path("tests/fixtures/context-routing-v0.1.json").read_text(encoding="utf-8")
        )
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
                    [item["heading"] for item in packet["sections"]],
                    case["headings"],
                    case["name"],
                )


if __name__ == "__main__":
    unittest.main()
