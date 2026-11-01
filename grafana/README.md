# Grafana CLI on MarcoPolo

Verified example: 2026-11-01, issue 133.
Use one-shot cron plus callback relay; confirm profile by independent dashboard readback.

## Before starting

- Reuse the installed official gcx 1.7.1 CLI. A new runtime must verify the release checksum.
- Check the existing Grafana profile first; do not initiate a second login if an authenticated read succeeds.
- Keep the user-approved profile private (0700 directory, 0600 file). Never commit its contents.
- The CLI requests Grafana API and Assistant permissions; show requested scopes before approval.

## Verified login route

1. Start the native gcx browser OAuth callback listener in MarcoPolo (not manual stdin mode).
2. Start the temporary HTTPS relay in the SAME durable execution. The one-shot cron recipe is the verified process-lifecycle boundary.
3. Check tunnel reachability before asking for browser approval. Only show the public approval URL, short check code and relay origin.
4. After approval, replace only the loopback origin in the browser address bar with the temporary HTTPS relay origin. Preserve the callback path and query unchanged.
5. Do NOT send the callback URL through ChatGPT or tool arguments. The browser delivers it directly to the CLI.

## Acceptance and cleanup

1. Require successful CLI completion AND an authenticated provider read from a separate new MarcoPolo invocation.
2. Read back the Session Search dashboard by its existing UID: session-search-candidate.
3. Confirm the cron entry, CLI listener and temporary SSH relay have stopped.
4. Remove temporary logs and run markers; retain only the private profile and pinned CLI.
5. Repeat the authenticated dashboard read after cleanup. Check profile permissions.

## Known failure boundaries

- A detached nohup process was not reliable across MarcoPolo executions; prefer proven one-shot cron.
- Manual stdin authorization introduced a needless chat/tool hop and was blocked before execution.
- The public tunnel URL alone proves nothing. Test reachability, callback completion, profile storage, and real Grafana readback separately.
- SSH output may contain carriage returns. Strip those before extracting the temporary HTTPS origin.
- A browser rendering error is not proof of a CLI failure; inspect the ongoing session first.

## Versioned install and recovery

From a current reviewed checkout of this cookbook, use the pinned Linux amd64 installer (v1.7.1):

```sh
grafana/gcx.sh --download     # explicit network access; checks pinned archive SHA-256
grafana/gcx.sh --install      # verifies extracted binary and installs OAuth helper
grafana/gcx.sh --check        # binary hash plus helper/source equality
```

Routine `grafana/gcx.sh <args>` does not download or authorize anything. The installed helper is `/workspace/tools/gcx/gcx-oauth-relay.sh`; its source is `grafana/gcx-oauth-relay.sh`. Do not copy OAuth profile files to Git or reset an already valid profile merely to test the installer.

Check the existing profile first. A new login is only for a missing, expired, or explicitly replaced session. After the user **explicitly approves unencrypted-at-rest storage** in this runtime, use:

```sh
GCX_FILE_STORAGE_APPROVED=1 /workspace/tools/gcx/gcx-oauth-relay.sh --schedule
/workspace/tools/gcx/gcx-oauth-relay.sh --status
```

The one-shot cron task launches the CLI and tunnel, deletes its schedule, and exposes the public login URL, verification code, and temporary HTTPS origin. After approval, the browser must deliver the callback directly to the tunnel, never to chat. `--cancel` revokes a queued login and its one-use approval; `--cleanup` removes transient logs after the login finishes. Preserve the private profile.

If the installed helper is absent, reinstall it from **the current reviewed Git source** using `--install`; the helper and its bytes must match the source. Never reuse an unreviewed runtime-local version.

After authorization, read back the saved profile without printing its contents:

```sh
D=/workspace/.config/gcx-tealaphid71
GCX_KEYCHAIN=off /workspace/tools/gcx/bin/gcx --context tealaphid71 config check --config "$D/config.yaml"
GCX_KEYCHAIN=off /workspace/tools/gcx/bin/gcx --context tealaphid71 dashboards get session-search-candidate --config "$D/config.yaml" --json metadata.name
```

The source for the Session Search dashboard belongs to `theseus-session-search-lab`, not `local-lab`. Grafana Cloud is shared runtime; CLI location does not transfer ownership.
