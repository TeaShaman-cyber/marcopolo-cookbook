#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

SCHEMA = "theseus.marcopolo-roadmap-snapshot.v1"
RECEIPT_SCHEMA = "theseus.marcopolo-roadmap-verification.v1"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "project-roadmap.json"


class ExportUnavailable(RuntimeError):
    pass


def stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_config(path: Path) -> dict[str, Any]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid roadmap config: {exc}") from exc
    if config.get("schema_version") != 1:
        raise ValueError("unsupported roadmap config schema_version")
    repository = config.get("repository")
    project = config.get("project")
    if not isinstance(repository, str) or "/" not in repository:
        raise ValueError("roadmap config repository must be OWNER/NAME")
    if not isinstance(project, dict):
        raise ValueError("roadmap config project missing")
    if project.get("owner_type") != "USER":
        raise ValueError("only USER-owned ProjectV2 is currently supported")
    if not isinstance(project.get("owner"), str) or not isinstance(
        project.get("number"), int
    ):
        raise ValueError("roadmap config project owner/number invalid")
    return config


def run_gh_graphql(query: str) -> dict[str, Any]:
    gh = os.environ.get("GH_BIN", "/workspace/.local/bin/gh")
    if not Path(gh).is_file():
        gh = "/usr/local/bin/gh"
    proc = subprocess.run(
        [gh, "api", "graphql", "-f", f"query={query}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ExportUnavailable(
            proc.stderr.strip() or f"gh graphql exited {proc.returncode}"
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ExportUnavailable("GitHub GraphQL returned invalid JSON") from exc
    if payload.get("errors"):
        raise ExportUnavailable(stable_json(payload["errors"]))
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ExportUnavailable("GitHub GraphQL response missing data")
    return data


def gql_string(value: str | None) -> str:
    return "null" if value is None else json.dumps(value)


def item_fields_fragment() -> str:
    return """
      fieldValues(first: 30) {
        nodes {
          ... on ProjectV2ItemFieldSingleSelectValue {
            name
            field { ... on ProjectV2FieldCommon { name } }
          }
        }
      }
    """


def normalize_fields(item: dict[str, Any]) -> dict[str, str]:
    values = item.get("fieldValues", {}).get("nodes", [])
    result: dict[str, str] = {}
    for value in values:
        if not isinstance(value, dict):
            continue
        field = value.get("field")
        name = value.get("name")
        if (
            isinstance(field, dict)
            and isinstance(field.get("name"), str)
            and isinstance(name, str)
        ):
            result[field["name"]] = name
    return result


def normalize_content(content: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(content, dict):
        return None
    repo = content.get("repository")
    repo_name = repo.get("nameWithOwner") if isinstance(repo, dict) else None
    number = content.get("number")
    url = content.get("url")
    title = content.get("title")
    typename = content.get("__typename")
    if (
        not isinstance(repo_name, str)
        or not isinstance(number, int)
        or not isinstance(url, str)
    ):
        return None
    if typename not in {"Issue", "PullRequest"}:
        return None
    return {
        "repository": repo_name,
        "entity_type": "ISSUE" if typename == "Issue" else "PULL_REQUEST",
        "number": number,
        "title": title if isinstance(title, str) else "",
        "url": url,
    }


def identity_key(entity: dict[str, Any]) -> tuple[str, str, int]:
    return (entity["repository"], entity["entity_type"], entity["number"])


def extract_markers(body: str | None) -> dict[str, Any]:
    text = body if isinstance(body, str) else ""
    parent = re.search(r"(?im)^Parent:\s*#(\d+)\s*$", text)
    disposition = re.search(
        r"(?im)^Disposition:\s*(ACTIVE|PARKED|MIGRATED|SUPERSEDED|COMPLETED|HISTORICAL|UNKNOWN)\s*$",
        text,
    )
    receipt = re.search(r"(?im)^Migration-Receipt:\s*(https://\S+)\s*$", text)
    owner = re.search(
        r"(?im)^(?:Owner-Issue|Refs?|Fixes|Closes):?\s*#(\d+)\b",
        text,
    )
    return {
        "parent_issue": int(parent.group(1)) if parent else None,
        "disposition": disposition.group(1).upper() if disposition else None,
        "migration_receipt_url": receipt.group(1) if receipt else None,
        "owner_issue": int(owner.group(1)) if owner else None,
    }


def project_page(config: dict[str, Any], after: str | None) -> dict[str, Any]:
    project = config["project"]
    query = f"""
    query {{
      user(login: {json.dumps(project["owner"])}) {{
        projectV2(number: {project["number"]}) {{
          id number title
          items(first: 100, after: {gql_string(after)}) {{
            totalCount
            pageInfo {{ hasNextPage endCursor }}
            nodes {{
              id isArchived
              content {{
                __typename
                ... on Issue {{ number title url repository {{ nameWithOwner }} }}
                ... on PullRequest {{ number title url repository {{ nameWithOwner }} }}
              }}
              {item_fields_fragment()}
            }}
          }}
        }}
      }}
    }}
    """
    data = run_gh_graphql(query)
    user = data.get("user")
    project_node = user.get("projectV2") if isinstance(user, dict) else None
    if not isinstance(project_node, dict):
        raise ExportUnavailable("configured ProjectV2 unavailable")
    return project_node


def export_project_connection(config: dict[str, Any]) -> dict[str, Any]:
    all_items: list[dict[str, Any]] = []
    after: str | None = None
    project_meta: dict[str, Any] | None = None
    reported_total: int | None = None
    for _ in range(20):
        node = project_page(config, after)
        if project_meta is None:
            project_meta = {
                "id": node.get("id"),
                "number": node.get("number"),
                "title": node.get("title"),
            }
        items = node.get("items")
        if not isinstance(items, dict):
            raise ExportUnavailable("ProjectV2 items connection unavailable")
        if reported_total is None and isinstance(items.get("totalCount"), int):
            reported_total = items["totalCount"]
        for item in items.get("nodes", []):
            if not isinstance(item, dict):
                continue
            content = normalize_content(item.get("content"))
            if content is None:
                continue
            all_items.append(
                {
                    **content,
                    "item_id": item.get("id"),
                    "is_archived": bool(item.get("isArchived")),
                    "fields": normalize_fields(item),
                }
            )
        page = items.get("pageInfo", {})
        if not page.get("hasNextPage"):
            break
        after = page.get("endCursor")
        if not isinstance(after, str):
            raise ExportUnavailable("ProjectV2 pagination cursor missing")
    else:
        raise ExportUnavailable("ProjectV2 pagination exceeded safety bound")
    assert project_meta is not None
    return {
        **project_meta,
        "reported_total_count": reported_total,
        "items": sorted(all_items, key=identity_key),
    }


def repository_page(
    config: dict[str, Any], kind: str, after: str | None
) -> dict[str, Any]:
    owner, name = config["repository"].split("/", 1)
    connection = "issues" if kind == "ISSUE" else "pullRequests"
    state_fields = "state stateReason" if kind == "ISSUE" else "state mergedAt"
    query = f"""
    query {{
      repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{
        {connection}(first: 100, after: {gql_string(after)}, orderBy: {{field: CREATED_AT, direction: ASC}}) {{
          pageInfo {{ hasNextPage endCursor }}
          nodes {{
            __typename id number title url body {state_fields}
            projectItems(first: 30) {{
              nodes {{
                id isArchived
                project {{ id number title }}
                {item_fields_fragment()}
              }}
            }}
          }}
        }}
      }}
    }}
    """
    data = run_gh_graphql(query)
    repository = data.get("repository")
    if not isinstance(repository, dict) or not isinstance(
        repository.get(connection), dict
    ):
        raise ExportUnavailable(f"repository {connection} connection unavailable")
    return repository[connection]


def export_repository_entities(config: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    project_number = config["project"]["number"]
    for kind in ("ISSUE", "PULL_REQUEST"):
        after: str | None = None
        for _ in range(20):
            page = repository_page(config, kind, after)
            for node in page.get("nodes", []):
                if not isinstance(node, dict) or not isinstance(
                    node.get("number"), int
                ):
                    continue
                memberships = []
                for item in node.get("projectItems", {}).get("nodes", []):
                    if not isinstance(item, dict):
                        continue
                    project = item.get("project")
                    if (
                        not isinstance(project, dict)
                        or project.get("number") != project_number
                    ):
                        continue
                    memberships.append(
                        {
                            "item_id": item.get("id"),
                            "is_archived": bool(item.get("isArchived")),
                            "fields": normalize_fields(item),
                        }
                    )
                markers = extract_markers(node.get("body"))
                entity = {
                    "repository": config["repository"],
                    "entity_type": kind,
                    "number": node["number"],
                    "title": node.get("title")
                    if isinstance(node.get("title"), str)
                    else "",
                    "url": node.get("url") if isinstance(node.get("url"), str) else "",
                    "state": node.get("state"),
                    "state_reason": node.get("stateReason")
                    if kind == "ISSUE"
                    else None,
                    "merged_at": node.get("mergedAt")
                    if kind == "PULL_REQUEST"
                    else None,
                    **markers,
                    "project_memberships": memberships,
                }
                result.append(entity)
            page_info = page.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            after = page_info.get("endCursor")
            if not isinstance(after, str):
                raise ExportUnavailable(f"repository {kind} pagination cursor missing")
        else:
            raise ExportUnavailable(
                f"repository {kind} pagination exceeded safety bound"
            )
    return sorted(result, key=identity_key)


def export_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": config["repository"],
        "project": export_project_connection(config),
        "entities": export_repository_entities(config),
    }


def finding(
    code: str, identity: tuple[str, str, int] | None = None, **details: Any
) -> dict[str, Any]:
    result: dict[str, Any] = {"code": code}
    if identity is not None:
        result["identity"] = {
            "repository": identity[0],
            "entity_type": identity[1],
            "number": identity[2],
        }
    if details:
        result["details"] = details
    return result


def verify_snapshot(snapshot: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    if snapshot.get("schema") != SCHEMA:
        raise ValueError("unsupported roadmap snapshot schema")
    entities = snapshot.get("entities")
    project = snapshot.get("project")
    if not isinstance(entities, list) or not isinstance(project, dict):
        raise ValueError("invalid roadmap snapshot structure")

    findings: list[dict[str, Any]] = []
    entity_map: dict[tuple[str, str, int], dict[str, Any]] = {}
    reverse_items: dict[tuple[str, str, int], dict[str, Any]] = {}
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        key = identity_key(entity)
        entity_map[key] = entity
        memberships = [
            m
            for m in entity.get("project_memberships", [])
            if isinstance(m, dict) and not m.get("is_archived")
        ]
        if len(memberships) > 1:
            findings.append(
                finding(
                    "DUPLICATE_ACTIVE_PROJECT_MEMBERSHIP", key, count=len(memberships)
                )
            )
        if memberships:
            reverse_items[key] = memberships[0]

    connection_items: dict[tuple[str, str, int], dict[str, Any]] = {}
    for item in project.get("items", []):
        if not isinstance(item, dict) or item.get("is_archived"):
            continue
        key = identity_key(item)
        if key in connection_items:
            findings.append(finding("DUPLICATE_PROJECT_CONNECTION_ITEM", key))
        connection_items[key] = item

    reverse_keys = set(reverse_items)
    connection_keys = set(connection_items)
    for key in sorted(reverse_keys - connection_keys):
        findings.append(
            finding(
                "PROJECT_CONNECTION_MISSING_ITEM",
                key,
                item_id=reverse_items[key].get("item_id"),
            )
        )
    for key in sorted(connection_keys - reverse_keys):
        findings.append(
            finding(
                "PROJECT_CONNECTION_ORPHAN_ITEM",
                key,
                item_id=connection_items[key].get("item_id"),
            )
        )
    reported_total = project.get("reported_total_count")
    if isinstance(reported_total, int) and reported_total != len(connection_items):
        findings.append(
            finding(
                "PROJECT_CONNECTION_TOTAL_MISMATCH",
                reported=reported_total,
                observed=len(connection_items),
            )
        )

    for key, item in reverse_items.items():
        entity = entity_map[key]
        fields = item.get("fields", {}) if isinstance(item.get("fields"), dict) else {}
        status = fields.get("Status")
        maturity = fields.get("Maturity")
        state = entity.get("state")
        if state in {"CLOSED", "MERGED"} and status == "In Progress":
            findings.append(finding("TERMINAL_ENTITY_IN_PROGRESS", key, state=state))
        if (
            state == "OPEN"
            and status == "Done"
            and maturity not in {"Parked", "Superseded"}
        ):
            findings.append(finding("OPEN_ENTITY_MARKED_DONE", key, maturity=maturity))
        if entity.get("disposition") == "MIGRATED" and not entity.get(
            "migration_receipt_url"
        ):
            findings.append(finding("MIGRATION_RECEIPT_MISSING", key))
        if key[1] == "PULL_REQUEST" and state == "OPEN":
            owner_issue = entity.get("owner_issue")
            exceptions = set(config.get("pr_owner_exceptions", []))
            if not isinstance(owner_issue, int) and key[2] not in exceptions:
                findings.append(finding("OPEN_PR_OWNER_ISSUE_MISSING", key))

    parent_number = config.get("cleanup_parent")
    child_numbers = config.get("cleanup_children", [])
    parent_key = (config["repository"], "ISSUE", parent_number)
    if parent_key not in reverse_items:
        findings.append(finding("CLEANUP_PARENT_NOT_IN_PROJECT", parent_key))
    for number in child_numbers:
        key = (config["repository"], "ISSUE", number)
        entity = entity_map.get(key)
        if entity is None:
            findings.append(finding("CLEANUP_CHILD_UNAVAILABLE", key))
            continue
        if key not in reverse_items:
            findings.append(finding("CLEANUP_CHILD_NOT_IN_PROJECT", key))
        if entity.get("parent_issue") != parent_number:
            findings.append(
                finding(
                    "CLEANUP_PARENT_MARKER_MISMATCH",
                    key,
                    expected=parent_number,
                    observed=entity.get("parent_issue"),
                )
            )

    findings.sort(
        key=lambda item: (
            item["code"],
            stable_json(item.get("identity", {})),
            stable_json(item.get("details", {})),
        )
    )
    return {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS" if not findings else "DRIFT",
        "project": {
            "owner": config["project"]["owner"],
            "number": config["project"]["number"],
            "title": project.get("title"),
        },
        "counts": {
            "entities": len(entity_map),
            "reverse_memberships": len(reverse_items),
            "connection_items": len(connection_items),
            "findings": len(findings),
        },
        "findings": findings,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def command_export(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    try:
        snapshot = export_snapshot(config)
    except ExportUnavailable as exc:
        payload = {"schema": RECEIPT_SCHEMA, "status": "UNAVAILABLE", "error": str(exc)}
        if args.output:
            write_json(args.output, payload)
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 2
    if args.output:
        write_json(args.output, snapshot)
    print(json.dumps(snapshot, ensure_ascii=False, sort_keys=True))
    return 0


def command_verify(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    try:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        receipt = verify_snapshot(snapshot, config)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        receipt = {"schema": RECEIPT_SCHEMA, "status": "UNAVAILABLE", "error": str(exc)}
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 2
    if args.receipt:
        write_json(args.receipt, receipt)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


def command_check(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    try:
        snapshot = export_snapshot(config)
        receipt = verify_snapshot(snapshot, config)
    except (ExportUnavailable, ValueError) as exc:
        receipt = {"schema": RECEIPT_SCHEMA, "status": "UNAVAILABLE", "error": str(exc)}
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 2
    if args.snapshot_output:
        write_json(args.snapshot_output, snapshot)
    if args.receipt:
        write_json(args.receipt, receipt)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export and verify the MarcoPolo GitHub Project roadmap graph."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("export")
    export.add_argument("--output", type=Path)
    export.set_defaults(func=command_export)

    verify = sub.add_parser("verify")
    verify.add_argument("snapshot", type=Path)
    verify.add_argument("--receipt", type=Path)
    verify.set_defaults(func=command_verify)

    check = sub.add_parser("check")
    check.add_argument("--snapshot-output", type=Path)
    check.add_argument("--receipt", type=Path)
    check.set_defaults(func=command_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
