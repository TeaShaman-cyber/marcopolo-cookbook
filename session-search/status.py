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


def _run(
    *args: str, cwd: pathlib.Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def _git(root: pathlib.Path, *args: str) -> str | None:
    proc = _run("git", "-C", str(root), *args)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_projection(
    tool_dir: pathlib.Path, canonical_dir: pathlib.Path, refresh: bool
) -> dict[str, Any]:
    mismatches: list[str] = []
    if not canonical_dir.is_dir():
        return {
            "state": "UNKNOWN",
            "mismatches": ["canonical_dir_missing"],
            "remote_state": "UNKNOWN" if refresh else "NOT_CHECKED",
        }

    if tool_dir.resolve() != canonical_dir.resolve():
        for name in RUNTIME_FILES:
            source = canonical_dir / name
            target = tool_dir / name
            if not source.is_file() or not target.is_file():
                mismatches.append(name)
                continue
            if _file_sha256(source) != _file_sha256(target):
                mismatches.append(name)

    canonical_head = _git(canonical_dir, "rev-parse", "HEAD")
    canonical_branch = _git(canonical_dir, "branch", "--show-current") or None
    expected_ref = os.environ.get("SESSION_SEARCH_CANONICAL_REF", "origin/main")
    local_ref_head = _git(canonical_dir, "rev-parse", expected_ref)
    remote_state = "NOT_CHECKED"
    remote_head = None
    if refresh:
        remote = expected_ref.split("/", 1)[0] if "/" in expected_ref else "origin"
        fetch_ref = (
            expected_ref.split("/", 1)[1] if "/" in expected_ref else expected_ref
        )
        proc = _run(
            "git", "-C", str(canonical_dir), "fetch", "--quiet", remote, fetch_ref
        )
        if proc.returncode != 0:
            remote_state = "UNAVAILABLE"
        else:
            remote_head = _git(canonical_dir, "rev-parse", expected_ref)
            if remote_head is None or canonical_head is None:
                remote_state = "UNKNOWN"
            else:
                remote_state = "CURRENT" if canonical_head == remote_head else "STALE"

    return {
        "state": (
            "SOURCE" if tool_dir.resolve() == canonical_dir.resolve() else "MATCH"
        )
        if not mismatches
        else "STALE",
        "mismatches": mismatches,
        "canonical_head": canonical_head,
        "canonical_branch": canonical_branch,
        "expected_ref": expected_ref,
        "local_ref_head": local_ref_head,
        "remote_state": remote_state,
        "remote_head": remote_head,
    }


def _implementation(root: pathlib.Path, refresh: bool) -> dict[str, Any]:
    search_py = root / "session_search" / "search.py"
    if not search_py.is_file():
        return {"state": "UNAVAILABLE", "root": str(root)}

    head = _git(root, "rev-parse", "HEAD")
    if head is None:
        return {"state": "UNKNOWN", "root": str(root), "reason": "git_head_unavailable"}

    relevant_dirty = _git(root, "status", "--porcelain", "--", "session_search")
    expected_head = os.environ.get("SESSION_SEARCH_IMPLEMENTATION_HEAD") or None
    expected_ref = os.environ.get("SESSION_SEARCH_IMPLEMENTATION_REF") or None
    branch = _git(root, "branch", "--show-current") or None
    upstream = _git(
        root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
    )
    bound_ref_head = _git(root, "rev-parse", expected_ref) if expected_ref else None

    local_state = "BOUND"
    reason = None
    if relevant_dirty:
        local_state = "DIRTY"
        reason = "tracked_or_untracked_session_search_changes"
    elif expected_head and head != expected_head:
        local_state = "STALE"
        reason = "head_mismatch"
    elif expected_ref and bound_ref_head is None:
        local_state = "UNKNOWN"
        reason = "bound_ref_unavailable"
    elif expected_ref and head != bound_ref_head:
        local_state = "STALE"
        reason = "bound_ref_mismatch"

    remote_state = "NOT_CHECKED"
    remote_head = None
    if refresh:
        ref = expected_ref or upstream
        if ref is None:
            remote_state = "UNKNOWN"
        else:
            remote = ref.split("/", 1)[0] if "/" in ref else "origin"
            fetch_ref = ref.split("/", 1)[1] if "/" in ref else ref
            proc = _run("git", "-C", str(root), "fetch", "--quiet", remote, fetch_ref)
            if proc.returncode != 0:
                remote_state = "UNAVAILABLE"
            else:
                remote_head = _git(root, "rev-parse", ref)
                if remote_head is None:
                    remote_state = "UNKNOWN"
                else:
                    remote_state = "CURRENT" if head == remote_head else "STALE"

    return {
        "state": local_state,
        "reason": reason,
        "root": str(root),
        "head": head,
        "branch": branch,
        "upstream": upstream,
        "expected_head": expected_head,
        "expected_ref": expected_ref,
        "bound_ref_head": bound_ref_head,
        "remote_state": remote_state,
        "remote_head": remote_head,
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
    observed_payload = (
        f"{accepted_token}:{accepted_count}:{stat.st_size}:{stat.st_mtime_ns}"
    )
    observed_token = hashlib.sha256(observed_payload.encode("ascii")).hexdigest()
    expected_token = os.environ.get("SESSION_SEARCH_CORPUS_TOKEN") or None
    state = "BOUND"
    reason = None
    if expected_token is not None and expected_token != observed_token:
        state = "STALE"
        reason = "observed_token_mismatch"
    return {
        "state": state,
        "reason": reason,
        "root": str(root),
        "db_bytes": stat.st_size,
        "db_mtime_ns": stat.st_mtime_ns,
        "accepted_count": accepted_count,
        "accepted_set_token": accepted_token,
        "observed_token": observed_token,
        "expected_token": expected_token,
        "integrity": "NOT_CHECKED",
    }


def _cache(corpus: dict[str, Any]) -> dict[str, Any]:
    raw = os.environ.get("SESSION_SEARCH_LOCAL_PROJECTION")
    if not raw:
        return {"state": "UNCONFIGURED"}
    path = pathlib.Path(raw)
    token_file = pathlib.Path(f"{raw}.source-token")
    if not path.is_file() or not token_file.is_file():
        return {"state": "STALE", "path": str(path), "reason": "cache_or_token_missing"}
    try:
        cached_token = token_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        return {"state": "UNKNOWN", "path": str(path), "reason": str(exc)}
    observed = corpus.get("observed_token")
    if not isinstance(observed, str):
        return {
            "state": "UNKNOWN",
            "path": str(path),
            "reason": "corpus_token_unavailable",
        }
    return {
        "state": "CURRENT" if cached_token == observed else "STALE",
        "path": str(path),
        "source_token": cached_token,
    }


def collect(refresh: bool) -> dict[str, Any]:
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
    corpus_root = pathlib.Path(corpus_raw) if corpus_raw else None

    runtime = _runtime_projection(tool_dir, canonical_dir, refresh)
    implementation = _implementation(implementation_root, refresh)
    corpus = _corpus(corpus_root)
    cache = _cache(corpus)

    blockers: list[str] = []
    if runtime["state"] in {"STALE", "UNKNOWN"}:
        blockers.append("runtime_projection")
    if implementation["state"] in {"UNAVAILABLE", "UNKNOWN", "DIRTY", "STALE"}:
        blockers.append("implementation")
    if corpus["state"] in {"UNRESOLVED", "UNAVAILABLE", "UNKNOWN", "STALE"}:
        blockers.append("corpus")
    local_state = "READY" if not blockers else "BLOCKED"
    if not refresh:
        remote_state = "NOT_CHECKED"
    else:
        remote_states = {
            runtime.get("remote_state"),
            implementation.get("remote_state"),
        }
        if "STALE" in remote_states:
            remote_state = "STALE"
        elif "UNAVAILABLE" in remote_states:
            remote_state = "UNAVAILABLE"
        elif remote_states == {"CURRENT"}:
            remote_state = "CURRENT"
        else:
            remote_state = "UNKNOWN"
    return {
        "schema": "theseus.session-search-runtime-status.v1",
        "local_state": local_state,
        "remote_currentness": remote_state,
        "blockers": blockers,
        "runtime_projection": runtime,
        "implementation": implementation,
        "corpus": corpus,
        "local_projection": cache,
        "semantics": {
            "local_ready_proves": "runtime/code/bound-corpus coherence only",
            "remote_freshness": "checked only with --refresh",
            "corpus_integrity": "not checked; use acceptance.sh for heavy verification",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cheap Session Search runtime/code/corpus freshness status."
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="perform bounded Git remote currentness refresh",
    )
    parser.add_argument(
        "--check-search",
        action="store_true",
        help="quiet success; emit only blocking diagnostics",
    )
    args = parser.parse_args(argv)
    status = collect(args.refresh)
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
        print(
            f"SESSION_SEARCH_STATUS local={status['local_state']} "
            f"remote={status['remote_currentness']} blockers={','.join(status['blockers']) or '-'}"
        )
        implementation = status["implementation"]
        corpus = status["corpus"]
        print(
            f"implementation state={implementation.get('state')} head={implementation.get('head') or '-'} "
            f"branch={implementation.get('branch') or '-'}"
        )
        print(
            f"corpus state={corpus.get('state')} accepted={corpus.get('accepted_count', '-')} "
            f"token={str(corpus.get('observed_token') or '-')[:16]}"
        )
        print(f"local_projection state={status['local_projection'].get('state')}")
    return 0 if ok else 69


if __name__ == "__main__":
    raise SystemExit(main())
