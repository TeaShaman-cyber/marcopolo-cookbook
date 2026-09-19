# Lightweight development gate

Small MarcoPolo development environment for catching mechanical mistakes before Codex review without creating a package-manager or plugin tree on persistent storage.

## Shape

```text
/workspace/.local/theseus-dev/bin/
  micro
  ruff
  shellcheck
  shfmt
```

The installed toolset is four standalone executables (about 54 MB in the current Linux x86-64 build). Download archives are staged in `/tmp`, verified against pinned SHA-256 digests, and discarded after installation.

No `node_modules`, Python virtualenv, Docker image, plugin manager, or language-server farm is created.

## Bootstrap

```sh
tools/dev/bootstrap.sh
tools/dev/bootstrap.sh --check
```

Pinned versions:

- Micro 2.0.15 static
- Ruff 0.16.6
- ShellCheck 0.11.0
- shfmt 3.14.0

## Edit

```sh
tools/dev/edit path/to/file
```

`edit` places Micro's configuration and backups under `/tmp/theseus-dev-cache/micro` by default so editor churn does not become persistent-workspace churn. Override `MICRO_CONFIG_HOME` explicitly if persistent editor preferences are actually wanted.

No third-party Micro plugins are installed by this route. Micro's built-in linter is reconfigured at launch through a one-file `/tmp` `init.lua`: Python uses Ruff `E9,F63,F7,F82`, shell uses ShellCheck at `warning` severity or higher with the known legacy-only `SC1090`/`SC1007` noise excluded, and shfmt is kept out of on-save diagnostics so formatting stays deterministic and explicit in `tools/dev/check`.

## Pre-Codex check

```sh
tools/dev/check
```

Default mode checks files changed from `origin/main` plus staged, unstaged, and untracked files. For deliberate whole-repository debt inspection:

```sh
tools/dev/check --all
```

The default gate is intentionally conservative:

- Python: Ruff `E9,F63,F7,F82`, Ruff format check, and `py_compile`;
- shell: ShellCheck at `warning` severity or higher with `SC1090`/`SC1007` excluded; shfmt is strict for new/previously clean files and skips pre-existing legacy shfmt debt in changed-file mode;
- JSON: `jq empty`;
- all changes: `git diff --check`;
- repository acceptance: Python tests, Python bootstrap acceptance, wiki-push acceptance.

Ruff cache lives under `/tmp/theseus-dev-cache/ruff`.

The gate intentionally does **not** treat stylistic or semantic heuristics as security failures. More opinionated rules can be evaluated later from measured signal rather than enabled wholesale.


## Canonical QA contract

`tools/dev/check` is the **canonical first local QA gate** for this repository.
Run it from the exact revision being evaluated before composing bespoke
pre-review checks.

The default invocation is:

```sh
tools/dev/check
```

Use `tools/dev/check --all` only for deliberate whole-repository debt
inspection. The ordinary gate is intentionally changed-file oriented.

Record the exact revision when a QA result is used as acceptance evidence. A
pass on another branch, an older checkout, or a different runtime is not proof
for the current candidate.

The local endpoint covers deterministic repository checks only. Separate
network/runtime witnesses are still required when a claim depends on GitHub,
MarcoPolo control-plane behavior, MCP/provider state, or other external
surfaces. Project metadata is likewise remote coordination state, not something
this local gate can establish by itself.

`QA PASS does not authorize` issue closure, migration, PR merge, release,
Project mutation, or any other consequential lifecycle transition. Those steps
remain subject to the repository lifecycle policy and exact remote readback.
