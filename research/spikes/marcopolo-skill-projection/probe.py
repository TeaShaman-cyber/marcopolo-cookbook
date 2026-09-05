from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
UPSTREAM = Path(os.environ.get("UPSTREAM_DIR", str(ROOT / "upstream"))).resolve()
SKILL_SOURCE = ROOT / "skills" / "candidates" / "using-theseus-marcopolo" / "SKILL.md"
OUT = ROOT / "research-output"
SKILL_REPO = OUT / "skill-repo"
SKILL_NAME = "using-theseus-marcopolo"
EXPECTED_UPSTREAM_SHA = "9c9ac20d605d131c010f174a64653e276bef81e8"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_sha(path: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
    ).strip()


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def extract_context_loader(
    path: Path, skill_document: type[Any], skill_registry: type[Any]
) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "CORE_SKILL_NAMES":
                selected.append(node)
        elif isinstance(node, ast.ClassDef) and node.name == "AgentBootstrapContext":
            selected.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "preload_core_skill_context":
                selected.append(node)

    names = {
        node.name
        for node in selected
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if "AgentBootstrapContext" not in names or "preload_core_skill_context" not in names:
        raise RuntimeError("pinned context_loader.py shape changed")

    module_ast = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__",
                names=[ast.alias(name="annotations")],
                level=0,
            ),
            ast.ImportFrom(
                module="dataclasses",
                names=[ast.alias(name="dataclass")],
                level=0,
            ),
            *selected,
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(module_ast)
    namespace: dict[str, Any] = {
        "SkillDocument": skill_document,
        "SkillRegistry": skill_registry,
    }
    exec(compile(module_ast, str(path), "exec"), namespace)
    return namespace


def extract_system_prompt(path: Path, bootstrap_context_type: type[Any]):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    func = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_system_prompt"
        ),
        None,
    )
    if func is None:
        raise RuntimeError("pinned runtime.py no longer defines _system_prompt")

    module_ast = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__",
                names=[ast.alias(name="annotations")],
                level=0,
            ),
            func,
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(module_ast)
    namespace: dict[str, Any] = {"AgentBootstrapContext": bootstrap_context_type}
    exec(compile(module_ast, str(path), "exec"), namespace)
    return namespace["_system_prompt"]


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    if not SKILL_SOURCE.is_file():
        raise SystemExit(f"missing canonical skill: {SKILL_SOURCE}")
    if not UPSTREAM.is_dir():
        raise SystemExit(f"missing pinned upstream checkout: {UPSTREAM}")

    upstream_sha = git_sha(UPSTREAM)
    if upstream_sha != EXPECTED_UPSTREAM_SHA:
        raise SystemExit(
            f"upstream identity mismatch: {upstream_sha} != {EXPECTED_UPSTREAM_SHA}"
        )

    if OUT.exists():
        shutil.rmtree(OUT)
    target_dir = SKILL_REPO / SKILL_NAME
    target_dir.mkdir(parents=True)
    copied_skill = target_dir / "SKILL.md"
    shutil.copy2(SKILL_SOURCE, copied_skill)

    skills_path = (
        UPSTREAM
        / "backend"
        / "app"
        / "services"
        / "platform"
        / "marcopolo"
        / "skills.py"
    )
    context_loader_path = (
        UPSTREAM
        / "backend"
        / "app"
        / "services"
        / "chatbot"
        / "ai_agent"
        / "context_loader.py"
    )
    runtime_path = (
        UPSTREAM
        / "backend"
        / "app"
        / "services"
        / "chatbot"
        / "ai_agent"
        / "runtime.py"
    )

    upstream_skills = load_module(skills_path, "pinned_marcopolo_skills")
    registry = upstream_skills.load_skill_registry(str(SKILL_REPO))
    skill = registry.get(SKILL_NAME)
    if skill is None:
        raise SystemExit("upstream SkillRegistry did not parse the Theseus skill")

    loader_ns = extract_context_loader(
        context_loader_path,
        upstream_skills.SkillDocument,
        upstream_skills.SkillRegistry,
    )
    upstream_core_names = tuple(loader_ns["CORE_SKILL_NAMES"])
    preload = loader_ns["preload_core_skill_context"]

    baseline = preload(registry)
    if SKILL_NAME in baseline.skill_names:
        raise SystemExit(
            "unexpected: untouched upstream CORE_SKILL_NAMES selected the Theseus skill"
        )

    loader_ns["CORE_SKILL_NAMES"] = (SKILL_NAME,)
    forced = preload(registry)
    if forced.skill_names != (SKILL_NAME,):
        raise SystemExit(
            f"forced selection failed: observed skill_names={forced.skill_names!r}"
        )

    system_prompt = extract_system_prompt(
        runtime_path, loader_ns["AgentBootstrapContext"]
    )(forced)

    skill_model = {
        "name": skill.name,
        "description": skill.description,
        "path": str(Path(skill.path).resolve().relative_to(ROOT)),
        "body": skill.body,
        "has_version_attribute": hasattr(skill, "version"),
    }
    baseline_model = {
        "upstream_core_skill_names": list(upstream_core_names),
        "registry_skill_names": [item.name for item in registry.summaries()],
        "baseline_preloaded_skill_names": list(baseline.skill_names),
        "theseus_skill_parsed": True,
        "theseus_skill_preloaded_by_untouched_upstream": False,
    }
    forced_model = {
        "test_only_core_skill_names": [SKILL_NAME],
        "preloaded_skill_names": list(forced.skill_names),
        "combined_text_bytes": len(forced.combined_text.encode("utf-8")),
    }

    write_json(OUT / "skill-document.json", skill_model)
    write_json(OUT / "baseline.json", baseline_model)
    write_json(OUT / "forced-selection.json", forced_model)
    (OUT / "combined-context.txt").write_text(
        forced.combined_text + "\n", encoding="utf-8"
    )
    (OUT / "system-prompt.txt").write_text(system_prompt + "\n", encoding="utf-8")

    receipt = {
        "classification": "PUBLIC_REFERENCE_CLIENT_PROJECTION_SPIKE",
        "upstream_repo": "immersa-co/marcopolo-integration-starter",
        "upstream_sha": upstream_sha,
        "theseus_repo_sha": git_sha(ROOT),
        "skill_source": str(SKILL_SOURCE.relative_to(ROOT)),
        "skill_sha256": sha256_file(SKILL_SOURCE),
        "upstream_files": {
            str(skills_path.relative_to(UPSTREAM)): sha256_file(skills_path),
            str(context_loader_path.relative_to(UPSTREAM)): sha256_file(
                context_loader_path
            ),
            str(runtime_path.relative_to(UPSTREAM)): sha256_file(runtime_path),
        },
        "observations": {
            "skill_registry_parsed_skill": True,
            "untouched_upstream_preloaded_skill": False,
            "test_only_name_override_preloaded_skill": True,
            "metadata_version_preserved_as_skilldocument_attribute": hasattr(
                skill, "version"
            ),
        },
        "projection": {
            "combined_context_sha256": sha256_bytes(
                (forced.combined_text + "\n").encode("utf-8")
            ),
            "system_prompt_sha256": sha256_bytes(
                (system_prompt + "\n").encode("utf-8")
            ),
        },
        "negative_boundaries": [
            "Does not exercise MarcoPolo app-managed skill:// resources.",
            "Does not prove ChatGPT or MarcoPolo automatic skill selection.",
            "Does not exercise host-level pre/post-turn lifecycle callbacks.",
            "Does not require or exercise live MarcoPolo MCP authentication.",
        ],
    }
    write_json(OUT / "receipt.json", receipt)

    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
