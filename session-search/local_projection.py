from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import pathlib
import sqlite3
import stat
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

SCHEMA = "theseus.session-search-local-projection.v1"
HEX = frozenset("0123456789abcdef")


class LocalProjectionError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class SourceGeneration:
    token: str
    accepted_ids: tuple[str, ...]
    db_stat: dict[str, int]


def _stable_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _source_key(corpus_root: pathlib.Path) -> str:
    absolute = os.path.abspath(os.fspath(corpus_root.expanduser()))
    return hashlib.sha256(absolute.encode("utf-8")).hexdigest()


def _accepted_artifact_ids(accepted_dir: pathlib.Path) -> tuple[str, ...]:
    try:
        entries = list(os.scandir(accepted_dir))
    except OSError as exc:
        raise LocalProjectionError("ACCEPTED_LEDGER_UNAVAILABLE") from exc

    ids: list[str] = []
    for entry in entries:
        if not entry.is_file(follow_symlinks=False):
            continue
        name = entry.name
        if not name.endswith(".json"):
            raise LocalProjectionError("ACCEPTED_LEDGER_NAME_INVALID")
        artifact_id = name[:-5]
        if len(artifact_id) != 64 or any(ch not in HEX for ch in artifact_id):
            raise LocalProjectionError("ACCEPTED_LEDGER_NAME_INVALID")
        ids.append(artifact_id)
    ids.sort()
    return tuple(ids)


def _db_identity(path: pathlib.Path) -> dict[str, int]:
    try:
        st = path.stat()
    except OSError as exc:
        raise LocalProjectionError("SOURCE_DB_UNAVAILABLE") from exc
    if not stat.S_ISREG(st.st_mode):
        raise LocalProjectionError("SOURCE_DB_UNAVAILABLE")
    return {
        "dev": int(st.st_dev),
        "ino": int(st.st_ino),
        "size": int(st.st_size),
        "mtime_ns": int(st.st_mtime_ns),
        "ctime_ns": int(st.st_ctime_ns),
    }


def observe_generation(corpus_root: pathlib.Path) -> SourceGeneration:
    corpus_root = pathlib.Path(corpus_root)
    accepted_ids = _accepted_artifact_ids(corpus_root / "ledger" / "accepted")
    db_stat = _db_identity(corpus_root / "corpus.sqlite3")
    digest = hashlib.sha256()
    digest.update(SCHEMA.encode("ascii"))
    digest.update(b"\0")
    for artifact_id in accepted_ids:
        digest.update(artifact_id.encode("ascii"))
        digest.update(b"\0")
    digest.update(_stable_json_bytes(db_stat))
    return SourceGeneration(digest.hexdigest(), accepted_ids, db_stat)


def _cache_paths(
    corpus_root: pathlib.Path, cache_root: pathlib.Path
) -> dict[str, pathlib.Path]:
    key = _source_key(corpus_root)
    root = pathlib.Path(cache_root) / key[:24]
    return {
        "root": root,
        "db": root / "corpus.sqlite3",
        "meta": root / "source-generation.json",
        "lock": root / ".refresh.lock",
    }


def _cache_file_identity(path: pathlib.Path) -> dict[str, int] | None:
    try:
        st = path.stat()
    except OSError:
        return None
    if not stat.S_ISREG(st.st_mode):
        return None
    return {
        "dev": int(st.st_dev),
        "ino": int(st.st_ino),
        "size": int(st.st_size),
        "mtime_ns": int(st.st_mtime_ns),
    }


def _read_metadata(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def _cache_is_current(paths: dict[str, pathlib.Path], source: SourceGeneration) -> bool:
    metadata = _read_metadata(paths["meta"])
    if not metadata or metadata.get("schema") != SCHEMA:
        return False
    if metadata.get("source_generation") != source.token:
        return False
    identity = _cache_file_identity(paths["db"])
    return identity is not None and identity == metadata.get("cache_db_stat")


def _readonly_sqlite_uri(path: pathlib.Path) -> str:
    return pathlib.Path(path).absolute().as_uri() + "?mode=ro"


def _backup_sqlite(source_db: pathlib.Path, candidate_db: pathlib.Path) -> None:
    try:
        source = sqlite3.connect(_readonly_sqlite_uri(source_db), uri=True)
    except sqlite3.Error as exc:
        raise LocalProjectionError("SOURCE_DB_OPEN_FAILED") from exc
    try:
        destination = sqlite3.connect(candidate_db)
        try:
            source.backup(destination)
            destination.commit()
        finally:
            destination.close()
    except sqlite3.Error as exc:
        raise LocalProjectionError("SQLITE_BACKUP_FAILED") from exc
    finally:
        source.close()


def _validate_candidate(
    candidate_db: pathlib.Path, accepted_ids: tuple[str, ...]
) -> None:
    try:
        conn = sqlite3.connect(_readonly_sqlite_uri(candidate_db), uri=True)
        try:
            local_ids = tuple(
                row[0]
                for row in conn.execute("SELECT sha256 FROM artifacts ORDER BY sha256")
            )
            if local_ids != accepted_ids:
                raise LocalProjectionError("CANDIDATE_MEMBERSHIP_MISMATCH")
            row = conn.execute("PRAGMA quick_check").fetchone()
            if row is None or row[0] != "ok":
                raise LocalProjectionError("CANDIDATE_QUICK_CHECK_FAILED")
        finally:
            conn.close()
    except LocalProjectionError:
        raise
    except sqlite3.Error as exc:
        raise LocalProjectionError("CANDIDATE_SQLITE_INVALID") from exc


def _atomic_write_metadata(path: pathlib.Path, payload: dict[str, Any]) -> None:
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temp.open("xb") as handle:
            handle.write(_stable_json_bytes(payload) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def _publish_candidate(
    candidate_db: pathlib.Path,
    paths: dict[str, pathlib.Path],
    corpus_root: pathlib.Path,
    generation: SourceGeneration,
) -> None:
    os.chmod(candidate_db, 0o444)
    os.replace(candidate_db, paths["db"])
    cache_stat = _cache_file_identity(paths["db"])
    if cache_stat is None:
        raise LocalProjectionError("CACHE_PUBLICATION_FAILED")
    metadata = {
        "schema": SCHEMA,
        "source_key": _source_key(corpus_root),
        "source_generation": generation.token,
        "accepted_count": len(generation.accepted_ids),
        "cache_db_stat": cache_stat,
        "published_at": _utc_now(),
    }
    _atomic_write_metadata(paths["meta"], metadata)


def ensure_local_projection(
    corpus_root: pathlib.Path,
    cache_root: pathlib.Path,
    *,
    max_attempts: int = 2,
) -> dict[str, Any]:
    corpus_root = pathlib.Path(corpus_root)
    cache_root = pathlib.Path(cache_root)
    paths = _cache_paths(corpus_root, cache_root)
    try:
        paths["root"].mkdir(parents=True, exist_ok=True)
        root_stat = paths["root"].lstat()
        if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
            raise LocalProjectionError("CACHE_ROOT_UNSAFE")
        if hasattr(os, "getuid") and root_stat.st_uid != os.getuid():
            raise LocalProjectionError("CACHE_ROOT_UNSAFE")
        os.chmod(paths["root"], 0o700)
    except LocalProjectionError:
        raise
    except OSError as exc:
        raise LocalProjectionError("CACHE_ROOT_UNAVAILABLE") from exc

    with paths["lock"].open("a+b") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        if (corpus_root / "mutation.lock").exists():
            raise LocalProjectionError("SOURCE_MUTATION_ACTIVE")
        source = observe_generation(corpus_root)
        if _cache_is_current(paths, source):
            return {
                "status": "CURRENT",
                "root": str(paths["root"]),
                "generation": source.token,
                "accepted_count": len(source.accepted_ids),
            }

        last_error = "SOURCE_CHANGED_DURING_REFRESH"
        for _attempt in range(max_attempts):
            before = observe_generation(corpus_root)
            fd, candidate_name = tempfile.mkstemp(
                prefix=".corpus.", suffix=".sqlite3.tmp", dir=paths["root"]
            )
            os.close(fd)
            candidate = pathlib.Path(candidate_name)
            try:
                _backup_sqlite(corpus_root / "corpus.sqlite3", candidate)
                after = observe_generation(corpus_root)
                if before.token != after.token:
                    last_error = "SOURCE_CHANGED_DURING_REFRESH"
                    continue
                _validate_candidate(candidate, after.accepted_ids)
                _publish_candidate(candidate, paths, corpus_root, after)
                if not _cache_is_current(paths, after):
                    raise LocalProjectionError("CACHE_PUBLICATION_READBACK_FAILED")
                return {
                    "status": "REFRESHED",
                    "root": str(paths["root"]),
                    "generation": after.token,
                    "accepted_count": len(after.accepted_ids),
                }
            finally:
                try:
                    candidate.unlink()
                except FileNotFoundError:
                    pass
        raise LocalProjectionError(last_error)


def _default_cache_root() -> pathlib.Path:
    return pathlib.Path(
        os.environ.get(
            "SESSION_SEARCH_LOCAL_CACHE_ROOT", "/tmp/session-search-local-projection"
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ensure a freshness-bound local Session Search read projection."
    )
    parser.add_argument("--corpus", default=os.environ.get("SESSION_SEARCH_CORPUS"))
    parser.add_argument(
        "--cache-root", default=os.environ.get("SESSION_SEARCH_LOCAL_CACHE_ROOT")
    )
    parser.add_argument(
        "--path", action="store_true", help="print only the usable local corpus root"
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.corpus:
        print(
            "SESSION_SEARCH_LOCAL_PROJECTION DEGRADED reason=CORPUS_LOCATION_UNRESOLVED",
            file=sys.stderr,
        )
        return 75
    cache_root = (
        pathlib.Path(args.cache_root) if args.cache_root else _default_cache_root()
    )
    try:
        result = ensure_local_projection(pathlib.Path(args.corpus), cache_root)
    except LocalProjectionError as exc:
        reason = exc.code
    except (OSError, sqlite3.Error):
        reason = "LOCAL_CACHE_IO_ERROR"
    else:
        reason = None
    if reason is not None:
        if args.json:
            print(json.dumps({"status": "DEGRADED", "reason": reason}, sort_keys=True))
        print(
            f"SESSION_SEARCH_LOCAL_PROJECTION DEGRADED reason={reason}",
            file=sys.stderr,
        )
        return 75

    if args.path:
        print(result["root"])
    elif args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(
            f"SESSION_SEARCH_LOCAL_PROJECTION status={result['status']} "
            f"accepted={result['accepted_count']} generation={result['generation'][:16]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
