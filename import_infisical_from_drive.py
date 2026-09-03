#!/usr/bin/env python3
import argparse
import json
import os
import stat
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ALLOWED_KEYS = ("INFISICAL_CLIENT_ID", "INFISICAL_CLIENT_SECRET")
DEFAULT_CONNECTION = "google-drive-20260723-0544"
DEFAULT_TARGET = Path("/workspace/.config/infisical/universal-auth.env")


def fail(code: str, exit_code: int) -> None:
    print(code)
    raise SystemExit(exit_code)


def download(connection: str, remote_path: str, local_path: Path) -> None:
    cmd = [
        "connection", "download", connection,
        "--remote-path", remote_path,
        "--local-path", str(local_path.relative_to(Path("/workspace"))),
        "--json",
    ]
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode != 0:
        fail("DOWNLOAD_FAILED", 20)
    try:
        result = json.loads(p.stdout)
    except json.JSONDecodeError:
        fail("DOWNLOAD_RECEIPT_INVALID", 21)
    if not result.get("success"):
        fail("DOWNLOAD_FAILED", 22)
    if not local_path.is_file():
        fail("DOWNLOAD_MISSING_LOCAL_FILE", 23)


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        fail("VALIDATION_FAILED", 30)

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            fail("VALIDATION_FAILED", 31)
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in ALLOWED_KEYS or key in values or not value:
            fail("VALIDATION_FAILED", 32)
        values[key] = value

    if set(values) != set(ALLOWED_KEYS):
        fail("VALIDATION_FAILED", 33)
    return values


def atomic_install(values: dict[str, str], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(target.parent, 0o700)

    fd, temp_name = tempfile.mkstemp(prefix=".infisical-auth-", dir=target.parent)
    tmp = Path(temp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            for key in ALLOWED_KEYS:
                f.write(f"{key}={values[key]}\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
        os.chmod(target, 0o600)
    finally:
        if tmp.exists():
            tmp.unlink()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote-path", required=True, help="Google Drive provider path or file ID")
    ap.add_argument("--connection", default=DEFAULT_CONNECTION)
    ap.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = ap.parse_args()

    tmp_dir = Path("/workspace/data/downloads")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    source = tmp_dir / f"drive-{uuid.uuid4().hex}.env"
    try:
        download(args.connection, args.remote_path, source)
        values = parse_env(source)
        atomic_install(values, args.target)

        mode = stat.S_IMODE(args.target.stat().st_mode)
        if mode != 0o600:
            fail("POSTCONDITION_FAILED", 40)
        if set(parse_env(args.target)) != set(ALLOWED_KEYS):
            fail("POSTCONDITION_FAILED", 41)

        print("AUTH_IMPORT_OK")
        print("keys=2")
        print("mode=600")
        print("source_removed=yes")
    finally:
        try:
            source.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
