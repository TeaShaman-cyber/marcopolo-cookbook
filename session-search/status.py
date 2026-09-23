from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from typing import Any

RUNTIME_FILES = (
    "search.sh",
    "acceptance.sh",
    "status.sh",
    "status.py",
    "runtime-bindings.sh",
)


def _run_git(root: pathlib.Path, *args: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def _file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_projection(
    tool_dir: pathlib.Path, canonical_dir: pathlib.Path
) -> dict[str, Any]:
    if tool_dir.resolve() == canonical_dir.resolve():
        return {
            "state": "SOURCE",
            "mismatches": [],
            "canonical_head": _run_git(canonical_dir, "rev-parse", "HEAD"),
        }
    if not canonical_dir.is_dir():
        return {"state": "UNKNOWN", "mismatches": ["canonical_dir_missing"]}

    mismatches: list[str] = []
    for name in RUNTIME_FILES:
        source = canonical_dir / name
        target = tool_dir / name
        if not source.is_file() or not target.is_file():
            mismatches.append(name)
            continue
        if _file_sha256(source) != _file_sha256(target):
            mismatches.append(name)
    return {
        "state": "MATCH" if not mismatches else "STALE",
        "mismatches": mismatches,
        "canonical_head": _run_git(canonical_dir, "rev-parse", "HEAD"),
    }


def _implementation(root: pathlib.Path) -> dict[str, Any]:
    if not (root / "session_search" / "search.py").is_file():
        return {"state": "UNAVAILABLE", "root": str(root)}

    head = _run_git(root, "rev-parse", "HEAD")
    if head is None:
        return {"state": "UNKNOWN", "root": str(root), "reason": "git_head_unavailable"}

    relevant_dirty = _run_git(root, "status", "--porcelain", "--", "session_search")
    expected_head = os.environ.get("SESSION_SEARCH_IMPLEMENTATION_HEAD") or None
    expected_ref = os.environ.get("SESSION_SEARCH_IMPLEMENTATION_REF") or None
    bound_ref_head = _run_git(root, "rev-parse", expected_ref) if expected_ref else None

    state = "BOUND"
    reason = None
    if relevant_dirty:
        state = "DIRTY"
        reason = "session_search_tree_dirty"
    elif expected_head and head != expected_head:
        state = "STALE"
        reason = "head_mismatch"
    elif expected_ref and bound_ref_head is None:
        state = "UNKNOWN"
        reason = "bound_ref_unavailable"
    elif expected_ref and head != bound_ref_head:
        state = "STALE"
        reason = "bound_ref_mismatch"

    return {
        "state": state,
        "reason": reason,
        "root": str(root),
        "head": head,
        "branch": _run_git(root, "branch", "--show-current") or None,
        "upstream": _run_git(
            root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
        ),
        "expected_head": expected_head,
        "expected_ref": expected_ref,
        "bound_ref_head": bound_ref_head,
        "remote_currentness": "NOT_CHECKED",
    }


def _accepted_set_token(accepted_dir: pathlib.Path) -> tuple[str, int]:
    names = sorted(
        entry.name
        for entry in os.scandir(accepted_dir)
        if entry.is_file(follow_symlinks=False)
    )
    digest = hashlib.sha256()
    for name in names:
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest(), len(names)


def _corpus(root: pathlib.Path | None) -> dict[str, Any]:
    if root is None:
        return {"state": "UNRESOLVED"}
    db = root / "corpus.sqlite3"
    accepted = root / "ledger" / "accepted"
    if not db.is_file() or not os.access(db, os.R_OK) or not accepted.is_dir():
        return {"state": "UNAVAILABLE", "root": str(root)}
    try:
        stat = db.stat()
        accepted_token, accepted_count = _accepted_set_token(accepted)
    except OSError as exc:
        return {"state": "UNKNOWN", "root": str(root), "reason": str(exc)}

    generation = hashlib.sha256(
        f"{accepted_token}:{accepted_count}:{stat.st_size}:{stat.st_mtime_ns}".encode()
    ).hexdigest()
    return {
        "state": "BOUND",
        "root": str(root),
        "db_bytes": stat.st_size,
        "accepted_count": accepted_count,
        "accepted_set_token": accepted_token,
        "observed_generation": generation,
        "integrity": "NOT_CHECKED",
    }


def collect() -> dict[str, Any]:
    tool_dir = pathlib.Path(__file__).resolve().parent
    canonical_dir = pathlib.Path(
        os.environ.get(
            "SESSION_SEARCH_CANONICAL_DIR",
            "/workspace/marcopolo-cookbook/session-search",
        )
    )
    implementation_root = pathlib.Path(
        os.environ.get(
            "SESSION_SEARCH_IMPLEMENTATION_ROOT",
            "/workspace/theseus-session-search-lab",
        )
    )
    corpus_raw = os.environ.get("SESSION_SEARCH_CORPUS")

    runtime = _runtime_projection(tool_dir, canonical_dir)
    implementation = _implementation(implementation_root)
    corpus = _corpus(pathlib.Path(corpus_raw) if corpus_raw else None)

    blockers: list[str] = []
    if runtime["state"] in {"STALE", "UNKNOWN"}:
        blockers.append("runtime_projection")
    if implementation["state"] in {"UNAVAILABLE", "UNKNOWN", "DIRTY", "STALE"}:
        blockers.append("implementation")
    if corpus["state"] in {"UNRESOLVED", "UNAVAILABLE", "UNKNOWN"}:
        blockers.append("corpus")

    return {
        "schema": "theseus.session-search-runtime-status.v1",
        "local_state": "READY" if not blockers else "BLOCKED",
        "blockers": blockers,
        "runtime_projection": runtime,
        "implementation": implementation,
        "corpus": corpus,
        "semantics": {
            "local_ready_proves": "runtime/code/bound-corpus coherence only",
            "remote_freshness": "NOT_CHECKED; use the workspace repository-currentness route when required",
            "corpus_integrity": "NOT_CHECKED; use acceptance.sh when required",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cheap local Session Search runtime/code/corpus status."
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--check-search",
        action="store_true",
        help="quiet success; emit only blocking diagnostics",
    )
    args = parser.parse_args(argv)
    status = collect()
    ok = status["local_state"] == "READY"

    if args.check_search:
        if not ok:
            print(
                "SESSION_SEARCH BLOCKED: LOCAL_FRESHNESS_CHECK_FAILED "
                + ",".join(status["blockers"]),
                file=sys.stderr,
            )
        return 0 if ok else 69

    if args.json:
        print(json.dumps(status, ensure_ascii=False, sort_keys=True))
    else:
        implementation = status["implementation"]
        corpus = status["corpus"]
        print(
            f"SESSION_SEARCH_STATUS local={status['local_state']} "
            f"blockers={','.join(status['blockers']) or '-'}"
        )
        print(
            f"implementation state={implementation.get('state')} "
            f"head={implementation.get('head') or '-'} "
            f"branch={implementation.get('branch') or '-'}"
        )
        print(
            f"corpus state={corpus.get('state')} "
            f"accepted={corpus.get('accepted_count', '-')} "
            f"generation={str(corpus.get('observed_generation') or '-')[:16]}"
        )
    return 0 if ok else 69


if __name__ == "__main__":
    raise SystemExit(main())
