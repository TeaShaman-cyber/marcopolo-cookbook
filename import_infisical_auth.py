#!/usr/bin/env python3
import argparse
import os
import stat
import tempfile
from pathlib import Path

ALLOWED = ("INFISICAL_CLIENT_ID", "INFISICAL_CLIENT_SECRET")
DEFAULT_DEST = Path("/workspace/.config/infisical/universal-auth.env")


def parse_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"invalid line {lineno}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in ALLOWED:
            raise ValueError(f"unexpected key on line {lineno}")
        if key in data:
            raise ValueError(f"duplicate key on line {lineno}")
        if not value:
            raise ValueError(f"empty value on line {lineno}")
        if "\x00" in value or "\n" in value or "\r" in value:
            raise ValueError(f"invalid value on line {lineno}")
        data[key] = value

    missing = [k for k in ALLOWED if k not in data]
    if missing:
        raise ValueError("missing required key(s)")
    if len(data) != len(ALLOWED):
        raise ValueError("unexpected key count")
    return data


def atomic_write(dest: Path, data: dict[str, str]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(dest.parent, 0o700)
    payload = "".join(f"{k}={data[k]}\n" for k in ALLOWED)

    fd, tmp_name = tempfile.mkstemp(prefix=".universal-auth.", dir=str(dest.parent), text=True)
    tmp = Path(tmp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, dest)
        os.chmod(dest, 0o600)
    finally:
        if tmp.exists():
            tmp.unlink()


def main() -> int:
    ap = argparse.ArgumentParser(description="Import Infisical Universal Auth credentials without printing secret values")
    ap.add_argument("source", type=Path)
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    ap.add_argument("--remove-source", action="store_true")
    args = ap.parse_args()

    src = args.source.resolve()
    if not src.is_file():
        raise SystemExit("SOURCE_NOT_FOUND")

    try:
        data = parse_env(src)
        atomic_write(args.dest, data)
    except Exception as exc:
        raise SystemExit(f"AUTH_IMPORT_FAILED:{exc}") from None

    st = args.dest.stat()
    if stat.S_IMODE(st.st_mode) != 0o600:
        raise SystemExit("AUTH_IMPORT_FAILED:bad_destination_mode")

    removed = "no"
    if args.remove_source:
        try:
            src.unlink()
            removed = "yes"
        except FileNotFoundError:
            removed = "already-missing"

    print("AUTH_IMPORT_OK")
    print("keys=2")
    print("mode=600")
    print(f"source_removed={removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
