from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "cookbook-routing-v0.1"
PACKET_VERSION = "cookbook-context-v0.1"
LABEL_KEY_RE = re.compile(r"^[a-z0-9_.-]+$")
ID_RE = re.compile(r"^[a-z0-9_.-]+$")
ROUTE_FIELDS = {"id", "match", "include", "sections"}
POLICY_FIELDS = {"sections"}


class ContextRoutingError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ContextRoutingError(code)


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ContextRoutingError("MANIFEST_INVALID")
    return value


def _route_map(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    routes = manifest.get("routes")
    _require(isinstance(routes, list), "ROUTES_INVALID")
    result: dict[str, Mapping[str, Any]] = {}
    for route in routes:
        _require(isinstance(route, Mapping), "ROUTE_INVALID")
        route_id = route.get("id")
        _require(
            isinstance(route_id, str) and ID_RE.fullmatch(route_id) is not None,
            "ROUTE_ID_INVALID",
        )
        if route_id in result:
            raise ContextRoutingError("ROUTE_ID_DUPLICATE")
        result[route_id] = route
    return result


def _policy_map(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    policies = manifest.get("policies")
    _require(isinstance(policies, Mapping), "POLICIES_INVALID")
    result: dict[str, Mapping[str, Any]] = {}
    for policy_id, policy in policies.items():
        _require(
            isinstance(policy_id, str) and ID_RE.fullmatch(policy_id) is not None,
            "POLICY_ID_INVALID",
        )
        _require(isinstance(policy, Mapping), "POLICY_INVALID")
        result[policy_id] = policy
    return result


def _visible_headings(lines: list[str]) -> list[tuple[int, int, str]]:
    headings: list[tuple[int, int, str]] = []
    fence_char: str | None = None
    fence_len = 0

    for index, raw_line in enumerate(lines):
        line = raw_line.rstrip("\r\n")
        fence = re.match(r"^[ ]{0,3}(`{3,}|~{3,})(.*)$", line)

        if fence_char is None:
            if fence is not None:
                marker = fence.group(1)
                fence_char = marker[0]
                fence_len = len(marker)
                continue
            heading = re.match(r"^(#{1,6})\s", line)
            if heading is not None:
                headings.append((index, len(heading.group(1)), line))
            continue

        closing = re.match(
            rf"^[ ]{{0,3}}{re.escape(fence_char)}{{{fence_len},}}[ \t]*$", line
        )
        if closing is not None:
            fence_char = None
            fence_len = 0

    return headings


def _validate_sections(sections: Any, repo_root: Path) -> None:
    _require(isinstance(sections, list), "SECTIONS_INVALID")
    root = repo_root.resolve()
    seen: set[tuple[str, str]] = set()

    for ref in sections:
        _require(isinstance(ref, Mapping), "SECTION_INVALID")
        path_value = ref.get("path")
        heading = ref.get("heading")
        _require(
            isinstance(path_value, str) and bool(path_value), "SECTION_PATH_INVALID"
        )
        _require(isinstance(heading, str) and bool(heading), "SECTION_HEADING_INVALID")

        candidate = (root / path_value).resolve()
        if not candidate.is_relative_to(root):
            raise ContextRoutingError("SECTION_PATH_ESCAPE")
        if not candidate.is_file():
            raise ContextRoutingError("SECTION_FILE_MISSING")

        key = (candidate.as_posix(), heading)
        if key in seen:
            raise ContextRoutingError("SECTION_DUPLICATE")
        seen.add(key)

        lines = candidate.read_text(encoding="utf-8").splitlines(keepends=True)
        count = sum(1 for _, _, text in _visible_headings(lines) if text == heading)
        if count == 0:
            raise ContextRoutingError("SECTION_HEADING_MISSING")
        if count > 1:
            raise ContextRoutingError("SECTION_HEADING_AMBIGUOUS")


def _validate_route(
    route: Mapping[str, Any], policies: Mapping[str, Any], repo_root: Path
) -> None:
    unknown = set(route).difference(ROUTE_FIELDS)
    if unknown:
        raise ContextRoutingError("ROUTE_FIELD_UNKNOWN")

    match = route.get("match")
    _require(isinstance(match, Mapping), "MATCH_INVALID")
    _require(bool(match), "ROUTE_MATCH_EMPTY")
    for key, value in match.items():
        _require(
            isinstance(key, str) and LABEL_KEY_RE.fullmatch(key) is not None,
            "LABEL_KEY_INVALID",
        )
        _require(isinstance(value, str), "MATCH_VALUE_INVALID")

    include = route.get("include")
    _require(isinstance(include, list), "POLICY_INCLUDE_INVALID")
    for policy_id in include:
        _require(isinstance(policy_id, str), "POLICY_INCLUDE_INVALID")
        if policy_id not in policies:
            raise ContextRoutingError("POLICY_INCLUDE_MISSING")

    _validate_sections(route.get("sections"), repo_root)


def validate_manifest(manifest: Mapping[str, Any], repo_root: Path) -> None:
    _require(isinstance(manifest, Mapping), "MANIFEST_INVALID")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ContextRoutingError("SCHEMA_VERSION_INVALID")

    defaults = manifest.get("defaults")
    _require(isinstance(defaults, Mapping), "DEFAULTS_INVALID")
    max_sections = defaults.get("max_sections")
    _require(isinstance(max_sections, int) and max_sections > 0, "MAX_SECTIONS_INVALID")
    fallback = defaults.get("fallback_route")
    _require(isinstance(fallback, str) and bool(fallback), "FALLBACK_ROUTE_INVALID")

    policies = _policy_map(manifest)
    for policy in policies.values():
        unknown = set(policy).difference(POLICY_FIELDS)
        if unknown:
            raise ContextRoutingError("POLICY_FIELD_UNKNOWN")
        _validate_sections(policy.get("sections"), repo_root)

    routes = _route_map(manifest)
    for route in routes.values():
        _validate_route(route, policies, repo_root)


def _route_matches(route: Mapping[str, Any], labels: Mapping[str, str]) -> bool:
    return all(labels.get(key) == expected for key, expected in route["match"].items())


def select_route(manifest: Mapping[str, Any], labels: Mapping[str, str]) -> str | None:
    routes = _route_map(manifest)
    matches = sorted(
        route_id for route_id, route in routes.items() if _route_matches(route, labels)
    )
    if not matches:
        return None
    if len(matches) > 1:
        raise ContextRoutingError("ROUTE_AMBIGUOUS")
    return matches[0]


def extract_section(repo_root: Path, ref: Mapping[str, str]) -> dict[str, str]:
    root = repo_root.resolve()
    path_value = ref.get("path")
    heading = ref.get("heading")
    _require(isinstance(path_value, str) and bool(path_value), "SECTION_PATH_INVALID")
    _require(isinstance(heading, str) and bool(heading), "SECTION_HEADING_INVALID")

    candidate = (root / path_value).resolve()
    if not candidate.is_relative_to(root):
        raise ContextRoutingError("SECTION_PATH_ESCAPE")
    if not candidate.is_file():
        raise ContextRoutingError("SECTION_FILE_MISSING")

    lines = candidate.read_text(encoding="utf-8").splitlines(keepends=True)
    headings = _visible_headings(lines)
    matches = [(index, level) for index, level, text in headings if text == heading]
    if not matches:
        raise ContextRoutingError("SECTION_HEADING_MISSING")
    if len(matches) > 1:
        raise ContextRoutingError("SECTION_HEADING_AMBIGUOUS")

    start, selected_level = matches[0]
    end = len(lines)
    for index, level, _ in headings:
        if index > start and level <= selected_level:
            end = index
            break

    return {
        "path": path_value,
        "heading": heading,
        "content": "".join(lines[start:end]),
    }


def compile_context(
    manifest: Mapping[str, Any], labels: Mapping[str, str], repo_root: Path
) -> dict[str, Any]:
    validate_manifest(manifest, repo_root)
    normalized_labels = dict(sorted(labels.items()))
    route_id = select_route(manifest, labels)
    fallback = manifest["defaults"]["fallback_route"]

    if route_id is None:
        return {
            "schema_version": PACKET_VERSION,
            "route_state": "UNKNOWN",
            "route_id": fallback,
            "labels": normalized_labels,
            "sections": [],
        }

    routes = _route_map(manifest)
    policies = _policy_map(manifest)
    route = routes[route_id]

    refs: list[Mapping[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add_refs(items: list[Mapping[str, str]]) -> None:
        for ref in items:
            key = (ref["path"], ref["heading"])
            if key in seen:
                continue
            seen.add(key)
            refs.append(ref)

    for policy_id in route["include"]:
        add_refs(policies[policy_id]["sections"])
    add_refs(route["sections"])

    if len(refs) > manifest["defaults"]["max_sections"]:
        raise ContextRoutingError("CONTEXT_BUDGET_EXCEEDED")

    return {
        "schema_version": PACKET_VERSION,
        "route_state": "MATCHED",
        "route_id": route_id,
        "labels": normalized_labels,
        "sections": [extract_section(repo_root, ref) for ref in refs],
    }
