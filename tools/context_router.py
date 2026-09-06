from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

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
        _require(isinstance(key, str) and LABEL_KEY_RE.fullmatch(key) is not None, "LABEL_KEY_INVALID")
        _require(isinstance(values, list) and all(isinstance(v, str) for v in values), "MATCH_VALUES_INVALID")
    for field, code in (("inherits", "INHERITS_INVALID"), ("inhibits", "INHIBITS_INVALID"), ("sections", "SECTIONS_INVALID")):
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
        _require(isinstance(path_value, str) and bool(path_value), "SECTION_PATH_INVALID")
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
        count = sum(1 for line in candidate.read_text(encoding="utf-8").splitlines() if line == heading)
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
