# Bootstrap Receipt — 2026-09-03

Repository: `TeaShaman-cyber/marcopolo-cookbook`

## Publication state

- Local initial commit: `13909e4278e610733621f59a970612d54b94ffab`
- Remote `origin/main`: `13909e4278e610733621f59a970612d54b94ffab`
- `git ls-remote` main: `13909e4278e610733621f59a970612d54b94ffab`
- Governed GitHub metadata: `{"defaultBranchRef":{"name":"main"},"nameWithOwner":"TeaShaman-cyber/marcopolo-cookbook","url":"https://github.com/TeaShaman-cyber/marcopolo-cookbook","visibility":"PRIVATE"}`
- Visibility observed through governed GitHub CLI: `PRIVATE`
- Default branch observed through governed GitHub CLI: `main`

## Local validation before publication

- curated allow-list staging: PASS
- generated/runtime exclusion check: PASS
- staged whitespace check: PASS after normalizing one CRLF/EOF issue in `wrapper-gh.sh`
- Bash syntax checks for staged shell scripts: PASS
- Python syntax checks for Infisical helper scripts: PASS
- mcporter acceptance: `PASS version=0.9.0`
- wiki-push acceptance: PASS for success, wrong-remote, dry-run-fail, push-fail, and mismatch scenarios

## Remote content verification

Representative expected files were verified in fetched `origin/main`, and generated/runtime classes `node_modules`, `__pycache__`, `*.pyc`, and `mcporter/traces/` were verified absent.

## Independent native GitHub readback

Disposition: **BLOCKED_CONNECTOR_SCOPE**.

The native GitHub connector returned `404` for the new private repository and reported no installed accounts/repositories during the verification attempt. This does not contradict the successful governed GitHub creation/push/fetch evidence; it means the intended independent GitHub App read path currently lacks usable installation scope in this conversation.

Bootstrap classification:

`REMOTE_PUBLISHED_GOVERNED_READBACK_VERIFIED / NATIVE_INDEPENDENT_READBACK_PENDING`

No visibility relaxation was used to work around this limitation.

## Follow-up: public visibility and native readback

After the initial private bootstrap was verified through the governed GitHub path, repository visibility was intentionally changed to `PUBLIC` because public release was already the intended destination after curated secret review.

Observed through governed GitHub metadata after the visibility change:

```json
{"defaultBranchRef":{"name":"main"},"nameWithOwner":"TeaShaman-cyber/marcopolo-cookbook","url":"https://github.com/TeaShaman-cyber/marcopolo-cookbook","visibility":"PUBLIC"}
```

Independent native GitHub connector readback then succeeded and confirmed:

- repository: `TeaShaman-cyber/marcopolo-cookbook`
- visibility: `public`
- default branch: `main`
- exact previously published commit `71f71e8d105c7ae41348d0cf9c170034c265ecb8` is readable through the native connector
- representative repository content is accessible through the public read path

The earlier `BLOCKED_CONNECTOR_SCOPE` observation remains valid historical evidence for the private state and is not deleted or rewritten.

Current bootstrap classification:

`REMOTE_PUBLISHED / PUBLIC / GOVERNED_READBACK_VERIFIED / NATIVE_INDEPENDENT_READBACK_VERIFIED`
