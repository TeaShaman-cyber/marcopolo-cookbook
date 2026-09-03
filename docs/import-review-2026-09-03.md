# Initial Import Review — 2026-09-03

Repository target: `TeaShaman-cyber/marcopolo-cookbook` (private-first).

## Review method

Candidate files were enumerated outside generated dependency/cache paths. Two bounded scans were performed before Git staging:

1. credential-keyword and suspicious-assignment scan reporting only filename, line number, and pattern class;
2. private-key-marker and high-entropy quoted-literal scan, with suspicious values redacted during manual inspection.

No private-key markers or embedded credential values were identified in the reviewed candidate set.

Authentication-related scripts refer to runtime-provided variables such as `INFISICAL_CLIENT_ID`, `INFISICAL_CLIENT_SECRET`, temporary access tokens, or governed GitHub configuration paths. Those values are not stored in the repository candidate files.

`mcporter/package-lock.json` contains normal npm integrity hashes; these are dependency integrity metadata, not credentials.

## SAFE_TO_COMMIT

- `.gitignore`
- `README.md`
- `README-github-wrapper.md`
- `check_access.sh`
- `check_project.sh`
- `import_infisical_auth.py`
- `import_infisical_from_drive.py`
- `jester-forum/README.md`
- `marcopolo/README.md`
- `mcporter/README.md`
- `mcporter/bin/mcporter`
- `mcporter/config/mcporter.json`
- `mcporter/package.json`
- `mcporter/package-lock.json`
- `mcporter/scripts/inventory.sh`
- `mcporter/tests/acceptance.sh`
- `search/README.md`
- `search/search.sh`
- `session-search/README.md`
- `session-search/search.sh`
- `tests/wiki-push.sh`
- `wiki-push.sh`
- `wrapper-gh.sh`
- `docs/superpowers/specs/2026-09-03-marcopolo-cookbook-design.md`
- `docs/superpowers/plans/2026-09-03-marcopolo-cookbook.md`
- `docs/import-review-2026-09-03.md`

## SAFE_AFTER_REDACTION

None in the initial reviewed set.

## EXCLUDE_RUNTIME_ONLY

- `mcporter/node_modules/`
- all `__pycache__/`
- all `*.pyc`
- `mcporter/traces/` pending a separate evidence/publication review
- virtual environments
- `.env` files and local environment overrides
- logs and temporary files

## BLOCKED_SECRET_OR_UNKNOWN

None in the initial reviewed candidate set.

## Publication rule

The first commit must stage only the explicit `SAFE_TO_COMMIT` paths. Runtime exclusions must remain absent from `git ls-files` after commit.
