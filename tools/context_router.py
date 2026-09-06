from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "cookbook-routing-v0.1"
LABEL_KEY_RE = re.compile(r"^[a-z0-9_.-]+$")


class ContextRoutingError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ContextRoutingError("MANIFEST_INVALID")
    return value


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ContextRoutingError(code)


def _route_map(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    routes = manifest.get("routes")
    _require(isinstance(routes, list), "ROUTES_INVALID")
    result: dict[str, Mapping[str, Any]] = {}
    for route in routes:
        _require(isinstance(route, Mapping), "ROUTE_INVALID")
        route_id = route.get("id")
        _require(isinstance(route_id, str) and bool(route_id), "ROUTE_ID_INVALID")
        if route_id in result:
            raise ContextRoutingError("ROUTE_ID_DUPLICATE")
        result[route_id] = route
    return result


def _validate_route_shape(route: Mapping[str, Any]) -> None:
    _require(isinstance(route.get("priority"), int), "ROUTE_PRIORITY_INVALID")
    match = route.get("match")
    _require(isinstance(match, Mapping), "MATCH_INVALID")
    for key, values in match.items():
        _require(
            isinstance(key, str) and LABEL_KEY_RE.fullmatch(key) is not None,
            "LABEL_KEY_INVALID",
        )
        _require(
            isinstance(values, list) and all(isinstance(v, str) for v in values),
            "MATCH_VALUES_INVALID",
        )
    for field, code in (
        ("inherits", "INHERITS_INVALID"),
        ("inhibits", "INHIBITS_INVALID"),
        ("sections", "SECTIONS_INVALID"),
    ):
        _require(isinstance(route.get(field), list), code)


def _validate_targets(routes: Mapping[str, Mapping[str, Any]]) -> None:
    ids = set(routes)
    for route in routes.values():
        for parent in route["inherits"]:
            _require(isinstance(parent, str), "INHERIT_TARGET_INVALID")
            if parent not in ids:
                raise ContextRoutingError("INHERIT_TARGET_MISSING")
        for target in route["inhibits"]:
            _require(isinstance(target, str), "INHIBIT_TARGET_INVALID")
            if target not in ids:
                raise ContextRoutingError("INHIBIT_TARGET_MISSING")


def _validate_inheritance_cycles(routes: Mapping[str, Mapping[str, Any]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(route_id: str) -> None:
        if route_id in visiting:
            raise ContextRoutingError("INHERITANCE_CYCLE")
        if route_id in visited:
            return
        visiting.add(route_id)
        for parent in routes[route_id]["inherits"]:
            visit(parent)
        visiting.remove(route_id)
        visited.add(route_id)

    for route_id in routes:
        visit(route_id)


def _validate_sections(route: Mapping[str, Any], repo_root: Path) -> None:
    root = repo_root.resolve()
    seen: set[tuple[str, str]] = set()
    for ref in route["sections"]:
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
        count = sum(
            1
            for line in candidate.read_text(encoding="utf-8").splitlines()
            if line == heading
        )
        if count == 0:
            raise ContextRoutingError("SECTION_HEADING_MISSING")
        if count > 1:
            raise ContextRoutingError("SECTION_HEADING_AMBIGUOUS")


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

    routes = _route_map(manifest)
    if fallback not in routes:
        raise ContextRoutingError("FALLBACK_ROUTE_MISSING")
    for route in routes.values():
        _validate_route_shape(route)
    _validate_targets(routes)
    _validate_inheritance_cycles(routes)
    for route in routes.values():
        _validate_sections(route, repo_root)


def _route_matches(route: Mapping[str, Any], labels: Mapping[str, str]) -> bool:
    return all(
        key in labels and labels[key] in allowed
        for key, allowed in route["match"].items()
    )


def select_route(manifest: Mapping[str, Any], labels: Mapping[str, str]) -> str | None:
    routes = _route_map(manifest)
    fallback = manifest["defaults"]["fallback_route"]
    matching = {
        route_id
        for route_id, route in routes.items()
        if route_id != fallback and _route_matches(route, labels)
    }
    if not matching:
        return None

    inhibited: set[str] = set()
    for route_id in matching:
        inhibited.update(routes[route_id]["inhibits"])
    survivors = matching.difference(inhibited)
    if not survivors:
        return None

    best_priority = max(routes[route_id]["priority"] for route_id in survivors)
    winners = sorted(
        route_id
        for route_id in survivors
        if routes[route_id]["priority"] == best_priority
    )
    if len(winners) != 1:
        raise ContextRoutingError("ROUTE_AMBIGUOUS")
    return winners[0]


def resolve_route_chain(manifest: Mapping[str, Any], route_id: str) -> list[str]:
    routes = _route_map(manifest)
    if route_id not in routes:
        raise ContextRoutingError("ROUTE_ID_UNKNOWN")

    result: list[str] = []
    emitted: set[str] = set()
    visiting: set[str] = set()

    def visit(current: str) -> None:
        if current in visiting:
            raise ContextRoutingError("INHERITANCE_CYCLE")
        if current in emitted:
            return
        visiting.add(current)
        for parent in routes[current]["inherits"]:
            visit(parent)
        visiting.remove(current)
        if current not in emitted:
            result.append(current)
            emitted.add(current)

    visit(route_id)
    return result


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
    matches = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == heading]
    if not matches:
        raise ContextRoutingError("SECTION_HEADING_MISSING")
    if len(matches) > 1:
        raise ContextRoutingError("SECTION_HEADING_AMBIGUOUS")

    heading_match = re.match(r"^(#{1,6})\s", heading)
    if heading_match is None:
        raise ContextRoutingError("SECTION_HEADING_INVALID")
    selected_level = len(heading_match.group(1))
    start = matches[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index].rstrip("\r\n")
        next_heading = re.match(r"^(#{1,6})\s", line)
        if next_heading is not None and len(next_heading.group(1)) <= selected_level:
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
    normalized_labels = dict(sorted(labels.items()))
    route_id = select_route(manifest, labels)
    fallback = manifest["defaults"]["fallback_route"]
    if route_id is None:
        return {
            "schema_version": "cookbook-context-v0.1",
            "route_state": "UNKNOWN",
            "route_id": fallback,
            "labels": normalized_labels,
            "sections": [],
        }

    routes = _route_map(manifest)
    refs: list[Mapping[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for chain_id in resolve_route_chain(manifest, route_id):
        for ref in routes[chain_id]["sections"]:
            key = (ref["path"], ref["heading"])
            if key in seen:
                continue
            seen.add(key)
            refs.append(ref)

    if len(refs) > manifest["defaults"]["max_sections"]:
        raise ContextRoutingError("CONTEXT_BUDGET_EXCEEDED")

    return {
        "schema_version": "cookbook-context-v0.1",
        "route_state": "MATCHED",
        "route_id": route_id,
        "labels": normalized_labels,
        "sections": [extract_section(repo_root, ref) for ref in refs],
    }
