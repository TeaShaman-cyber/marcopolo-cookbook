from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_metadata(package: dict[str, Any], metadata: dict[str, Any]) -> None:
    if metadata.get("expired"):
        raise RuntimeError("pinned package artifact is expired")
    if int(metadata.get("id", -1)) != int(package["artifact_id"]):
        raise RuntimeError("artifact id mismatch")
    if metadata.get("name") != package["artifact_name"]:
        raise RuntimeError("artifact name mismatch")
    if metadata.get("digest") != package["artifact_digest"]:
        raise RuntimeError("artifact digest mismatch")

    run = metadata.get("workflow_run") or {}
    if int(run.get("id", -1)) != int(package["run_id"]):
        raise RuntimeError("artifact workflow run mismatch")

    declared_head = package.get("builder_head_sha")
    if declared_head and run.get("head_sha") != declared_head:
        raise RuntimeError("artifact builder head mismatch")


def fetch_metadata(package: dict[str, Any]) -> dict[str, Any]:
    repository = package["repository"]
    cp = subprocess.run(
        [
            "gh",
            "api",
            "-H",
            "Accept: application/vnd.github+json",
            f"repos/{repository}/actions/artifacts/{package['artifact_id']}",
        ],
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    metadata = json.loads(cp.stdout)
    verify_metadata(package, metadata)
    return metadata


def download_archive(package: dict[str, Any], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    repository = package["repository"]
    with target.open("wb") as stream:
        subprocess.run(
            [
                "gh",
                "api",
                "-H",
                "Accept: application/vnd.github+json",
                f"repos/{repository}/actions/artifacts/{package['artifact_id']}/zip",
            ],
            stdout=stream,
            check=True,
            timeout=180,
        )


def _safe_destination(root: Path, member: str) -> Path:
    root = root.resolve()
    destination = (root / member).resolve()
    if destination != root and root not in destination.parents:
        raise RuntimeError(f"unsafe archive member: {member}")
    return destination


def safe_extract_zip(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            _safe_destination(target, member.filename)
        zipped.extractall(target)


def safe_extract_tar(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as packed:
        for member in packed.getmembers():
            _safe_destination(target, member.name)
            if member.issym() or member.islnk():
                raise RuntimeError(f"archive links are not allowed: {member.name}")
        try:
            packed.extractall(target, filter="data")
        except TypeError:
            packed.extractall(target)


def verify_and_extract(
    package: dict[str, Any],
    metadata: dict[str, Any],
    archive: Path,
    *,
    staging_dir: Path,
    runtime_dir: Path,
) -> dict[str, Any]:
    verify_metadata(package, metadata)

    digest = package["artifact_digest"]
    if not digest.startswith("sha256:"):
        raise RuntimeError(f"unsupported artifact digest: {digest}")

    expected_outer = digest.removeprefix("sha256:")
    observed_outer = sha256_file(archive)
    if observed_outer != expected_outer:
        raise RuntimeError("downloaded artifact digest mismatch")

    shutil.rmtree(staging_dir, ignore_errors=True)
    staging_dir.mkdir(parents=True, exist_ok=True)
    safe_extract_zip(archive, staging_dir)

    tar_path = staging_dir / package["tar_file"]
    if not tar_path.is_file():
        raise RuntimeError("toolchain tarball missing from artifact")

    observed_tar = sha256_file(tar_path)
    if observed_tar != package["tar_sha256"]:
        raise RuntimeError("toolchain tar sha mismatch")

    shutil.rmtree(runtime_dir, ignore_errors=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    safe_extract_tar(tar_path, runtime_dir)

    return {
        "archive_sha256": observed_outer,
        "tar_sha256": observed_tar,
        "runtime_dir": str(runtime_dir.resolve()),
    }
