# MarcoPolo Cookbook Design

## Purpose

Turn the existing `/workspace/tools` directory into a durable Git/GitHub project named `marcopolo-cookbook` without blindly publishing runtime debris, dependencies, credentials, or unreviewed raw traces.

The repository is a practical cookbook and toolbox for reusable MarcoPolo-related workflows: shell/connector field notes, Session Search, mcporter wrappers, search helpers, GitHub/wiki wrappers, tests, and future bounded recipes.

## Repository identity

- GitHub repository name: `marcopolo-cookbook`
- Owner: `TeaShaman-cyber`
- Initial visibility: **private**
- Local source directory: `/workspace/tools`
- Default branch: `main`
- Initial import policy: **curated import**, never `git add .` before review

## Scope

### Included in the initial repository

- `marcopolo/README.md`
- `session-search/README.md`
- `session-search/search.sh`
- `mcporter/README.md`
- `mcporter/package.json`
- `mcporter/package-lock.json`
- `mcporter/bin/`
- `mcporter/scripts/`
- `mcporter/tests/`
- `search/`
- `jester-forum/`
- top-level wrapper/helper scripts that pass review
- top-level tests that pass review
- this design document and later implementation plans
- a new root `README.md`
- a new `.gitignore`

### Excluded from the initial repository

- `mcporter/node_modules/`
- all `__pycache__/`
- `*.pyc`
- virtualenvs or generated dependency trees
- credential files, tokens, cookies, auth caches, or environment dumps
- unreviewed `mcporter/traces/*.json`
- transient logs, temporary files, downloaded artifacts, or generated caches

Raw traces may be added later only after an explicit content review establishes that they are safe and useful as public/private fixtures or evidence.

## Directory model

```text
marcopolo-cookbook/
├── README.md
├── .gitignore
├── docs/
│   └── superpowers/
│       ├── specs/
│       └── plans/
├── marcopolo/
│   └── README.md
├── session-search/
│   ├── README.md
│   └── search.sh
├── mcporter/
│   ├── README.md
│   ├── package.json
│   ├── package-lock.json
│   ├── bin/
│   ├── scripts/
│   └── tests/
├── search/
├── jester-forum/
├── tests/
├── wrapper-gh.sh
└── wiki-push.sh
```

The root README acts as an index, not a duplicate of component documentation.

## Security and import policy

The first commit must be constructed from an allow-list after a bounded security review.

### Secret review

Before staging files:

1. enumerate candidate files outside ignored/generated directories;
2. scan text for credential-related patterns without printing secret values;
3. manually inspect files that reference authentication, tokens, cookies, Infisical, GitHub auth, or environment variables;
4. classify each candidate as:
   - `SAFE_TO_COMMIT`
   - `SAFE_AFTER_REDACTION`
   - `EXCLUDE_RUNTIME_ONLY`
   - `BLOCKED_SECRET_OR_UNKNOWN`
5. stage only files explicitly classified as safe.

Credential-management scripts may be committed if they contain only logic, variable names, paths, and documented interfaces, but never embedded credential values or dumps.

## Git hygiene

`.gitignore` must cover at minimum:

```text
**/node_modules/
**/__pycache__/
*.py[cod]
.venv/
venv/
.env
.env.*
*.log
.DS_Store
```

Additional runtime-specific paths discovered during the preflight review must be added before the first commit.

The import process must not use a broad `git add .` until the ignore rules and allow-list review have both completed. Prefer explicit paths for the initial commit.

## GitHub publication flow

```text
/workspace/tools
      ↓
security + generated-file review
      ↓
git init -b main
      ↓
curated initial commit
      ↓
create private TeaShaman-cyber/marcopolo-cookbook
      ↓
governed GitHub write path
      ↓
independent GitHub readback
```

GitHub write and readback authority remain separate when possible:

```text
WRITE
  MarcoPolo governed gh-write / supported GitHub mutation path

READBACK
  native GitHub connector
```

The remote repository is not considered established until owner/name, visibility, default branch, HEAD commit, and expected files have been independently read back.

## Root README responsibilities

The root README will explain:

- what `marcopolo-cookbook` is;
- that recipes are based on observed operational work rather than hypothetical examples;
- component map;
- runtime boundaries (`/workspace` vs conversation runtime vs GitHub Actions);
- installation/reproduction expectations;
- security rule that credentials are referenced, never stored;
- links to component READMEs;
- contribution/update rule: reusable incident lessons belong in the cookbook, one-off transient events remain session evidence.

## Validation

Before remote creation:

1. `git status --short` contains only intentional candidates;
2. ignored directories are absent from `git ls-files`;
3. no candidate file fails the bounded secret review;
4. shell scripts pass `bash -n` where they are Bash scripts;
5. existing lightweight acceptance tests are run where practical;
6. `git diff --cached --check` is clean;
7. first commit hash is recorded.

After remote creation:

1. fetch/read the remote default branch;
2. verify remote HEAD equals the local intended commit;
3. verify repository visibility is private;
4. verify representative included files exist;
5. verify excluded runtime directories are absent;
6. record exact repository URL and initial commit in the completion note.

## Non-goals

This initial migration does **not**:

- redesign Session Search;
- redesign mcporter;
- convert the cookbook into a package manager;
- publish raw historical traces automatically;
- make the repository public;
- introduce CI beyond minimal validation needed for the initial repository;
- migrate unrelated project repositories into this repository.

Those are separate future changes.

## Success criteria

The migration is complete when:

- `/workspace/tools` is a clean Git repository on `main`;
- the first commit contains only reviewed, reproducible project files;
- generated dependencies and caches are ignored;
- no known credential material is committed;
- `TeaShaman-cyber/marcopolo-cookbook` exists as a private GitHub repository;
- native readback confirms exact initial HEAD and expected content;
- the existing MarcoPolo field guide, Session Search, and mcporter workbench are preserved as independently understandable components.
