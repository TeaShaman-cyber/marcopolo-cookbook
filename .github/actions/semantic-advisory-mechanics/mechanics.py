from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from artifact_package import download_archive, fetch_metadata, verify_and_extract
from package_freshness import _git_head, _hf_head, evaluate_freshness
from trace_input import build_manifest


def _write_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    with open(output, "a", encoding="utf-8") as stream:
        stream.write(f"{name}={value}\n")


def _freshness(config: dict) -> dict:
    package = config["package"]
    policy = config["freshness"]
    errors: list[str] = []
    current_git_sha = None
    current_hf_revision = None

    if policy.get("git_url") and config.get("source_sha"):
        try:
            current_git_sha = _git_head(
                policy["git_url"], policy.get("git_ref", "refs/heads/main")
            )
        except Exception as exc:
            errors.append(f"git_currentness:{type(exc).__name__}:{exc}")

    if policy.get("hf_repo") and config.get("model_revision"):
        try:
            current_hf_revision = _hf_head(policy["hf_repo"])
        except Exception as exc:
            errors.append(f"hf_currentness:{type(exc).__name__}:{exc}")

    return {
        **evaluate_freshness(
            now=datetime.now(timezone.utc),
            built_at=package.get("built_at"),
            expires_at=package.get("expires_at"),
            max_age_days=int(policy.get("max_age_days", 30)),
            expiry_warning_days=int(policy.get("expiry_warning_days", 14)),
            pinned_git_sha=config.get("source_sha"),
            current_git_sha=current_git_sha,
            pinned_hf_revision=config.get("model_revision"),
            current_hf_revision=current_hf_revision,
            currentness_errors=errors,
        ),
        "pinned_git_sha": config.get("source_sha"),
        "current_git_sha": current_git_sha,
        "pinned_hf_revision": config.get("model_revision"),
        "current_hf_revision": current_hf_revision,
        "blocking": False,
    }


def main() -> int:
    profile_path = Path(os.environ["SEMANTIC_PROFILE_FILE"])
    tool = os.environ["SEMANTIC_TOOL"]
    output_root = Path(os.environ["SEMANTIC_OUTPUT_ROOT"]).resolve()
    runtime_dir = Path(os.environ["SEMANTIC_RUNTIME_DIR"]).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    profiles = json.loads(profile_path.read_text())
    config = profiles[tool]
    budget = profiles["input_budget"]
    input_root = output_root / "input"

    manifest = build_manifest(
        Path("."),
        os.environ["SEMANTIC_BASE_SHA"],
        os.environ["SEMANTIC_CANDIDATE_SHA"],
        input_root,
        os.environ["SEMANTIC_REPOSITORY"],
        os.environ["SEMANTIC_TASK_ID"],
        max_files=int(budget["max_files"]),
        max_total_bytes=int(budget["max_total_bytes"]),
        max_file_bytes=int(budget["max_file_bytes"]),
    )
    freshness = _freshness(config)

    package_status = "SKIPPED_NO_SIGNAL"
    package_receipt: dict = {"status": package_status}

    if manifest["status"] != "NO_SIGNAL":
        try:
            metadata = fetch_metadata(config["package"])
            archive = output_root / "package-download" / "artifact.zip"
            download_archive(config["package"], archive)
            verified = verify_and_extract(
                config["package"],
                metadata,
                archive,
                staging_dir=output_root / "package-download" / "artifact",
                runtime_dir=runtime_dir,
            )
            package_status = "READY"
            package_receipt = {
                "status": package_status,
                "metadata": {
                    "id": metadata.get("id"),
                    "name": metadata.get("name"),
                    "digest": metadata.get("digest"),
                    "expires_at": metadata.get("expires_at"),
                    "workflow_run": metadata.get("workflow_run"),
                },
                **verified,
            }
        except Exception as exc:
            package_status = "UNAVAILABLE"
            package_receipt = {
                "status": package_status,
                "error": f"{type(exc).__name__}: {exc}",
            }

    receipt = {
        "schema_version": 1,
        "tool": tool,
        "repository": manifest["repository"],
        "task_id": manifest["task_id"],
        "base_sha": manifest["base_sha"],
        "candidate_sha": manifest["candidate_sha"],
        "input_status": manifest["status"],
        "freshness": freshness,
        "package": package_receipt,
        "acceptance_authority": False,
    }
    receipt_path = output_root / "mechanics-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    _write_output("input-status", manifest["status"])
    _write_output("freshness-status", freshness["status"])
    _write_output("package-status", package_status)
    _write_output("input-manifest", str((input_root / "input-manifest.json").resolve()))
    _write_output("input-root", str(input_root))
    _write_output("runtime-dir", str(runtime_dir))
    _write_output("receipt-path", str(receipt_path))

    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
