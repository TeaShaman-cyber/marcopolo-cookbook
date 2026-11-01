# GitHub wrapper — LEGACY / RECOVERY ONLY

Status: `SUPERSEDED_AS_PRIMARY_ROUTE`
Superseded: 2026-08-28

`/workspace/tools/wrapper-gh.sh` is retained for historical and recovery provenance. It is not the normal GitHub route in the current MarcoPolo workspace.

## Current route

```text
workspace_shell -> gh / git -> GitHub
```

The normal MarcoPolo route uses ordinary `gh` / `git`, with scope-separated authorization. The default MarcoPolo OAuth profile is read-capable; explicitly authorized writes use the separate `/workspace/.config/gh-write` CLI OAuth profile via `GH_CONFIG_DIR`. For bounded current-state inspection, the native ChatGPT GitHub plugin is also an allowed lightweight read route. Native plugin writes are explicit fallbacks only when MarcoPolo transport, quoting, or request-filter mechanics make the already-authorized mutation less safe or needlessly complex. After authorization or runtime changes, check the intended profile, run the smallest repository probe, and verify remote state after writes.

## When the old wrapper may be considered

Do not select `wrapper-gh.sh` merely because a direct route returned `403` or a quoting-sensitive command failed. First classify the failure. The wrapper may be considered only for verified auth/transport unavailability when current user intent already authorizes the same mutation, the normal governed route and native-plugin fallback are unsuitable, and the wrapper path is freshly re-verified. A semantic, policy, or repository-state rejection is a STOP condition, not permission to retry through the wrapper. Its existence on disk is not evidence that it is current or authorized.

Do not inspect or print credential values while diagnosing either route.

## Historical provenance

Older receipts and publisher scripts may contain commands such as:

```text
/workspace/tools/wrapper-gh.sh gh repo view ...
/workspace/tools/wrapper-gh.sh git push ...
```

Treat those as historical instructions tied to the older Infisical-backed route, not as current operating guidance.

## Expanding GitHub OAuth scopes in headless MarcoPolo

The write profile is isolated at `/workspace/.config/gh-write`. Scope expansion and profile reconstruction must target this profile explicitly and must be verified after the browser/device step.

Detached `nohup ... &` is not a supported recovery boundary in the current MarcoPolo runtime: supervised `workspace_shell` executions may terminate detached children when the call ends. Use the cron-backed one-shot helper instead:

```bash
/workspace/marcopolo-cookbook/github-write-oauth-recover.sh --schedule-login
```

The helper installs one tagged cron entry. On the first cron tick it atomically marks the flow started, removes its own cron entry before invoking GitHub CLI, and then waits for the GitHub device flow independently of the creating `workspace_shell` call. Repeated cron invocations or repeated `--run-login` calls cannot start a second flow.

Read only the sanitized operator-facing state:

```bash
/workspace/marcopolo-cookbook/github-write-oauth-recover.sh --status
```

`--status` exposes only the one-time device code, the GitHub device URL, and the recovery state. The raw GitHub CLI login log remains private in the temporary recovery state directory and is not printed.

Open `https://github.com/login/device`, enter the displayed one-time code, and approve the requested OAuth access. Browser approval alone is not success. The helper claims `VERIFIED` only after all three postconditions hold:

```text
/workspace/.config/gh-write/hosts.yml exists
github-git-auth.sh --install succeeds
github-write-preflight.sh --check succeeds
```

After a verified or failed flow, remove only the recovery schedule/state:

```bash
/workspace/marcopolo-cookbook/github-write-oauth-recover.sh --cleanup
```

The resulting `gh-write` profile is intentionally preserved by cleanup.

The helper owns one versioned canonical scope set for project-required GitHub capabilities. Every new OAuth login requests that complete set, so adding Codespaces does not drop Projects access (or vice versa). `GH_WRITE_OAUTH_SCOPES` is only for an explicitly requested extra scope; it is merged with the canonical set rather than replacing it. Do not use one-off scope lists for normal project capabilities.

After browser approval, verify the capabilities through their provider-native probes. In particular, Projects and Codespaces remain separate capability surfaces:

```bash
GH_CONFIG_DIR=/workspace/.config/gh-write gh project list --owner TeaShaman-cyber --format json
GH_CONFIG_DIR=/workspace/.config/gh-write gh codespace list --repo TeaShaman-cyber/theseus-session-search-lab
```

### Historical note

A 2026-08-30 device-flow experiment succeeded with a detached process in an earlier runtime, but the reconstructed 2026-11 runtime verified a different lifecycle: a detached canary did not survive `workspace_shell`, while a cron-launched canary did. The cron-backed helper therefore supersedes the old detached-`nohup` recipe.

Browser authorization, stored credential state, Git helper binding, and executable provider capability remain separate postconditions.

## GitHub Wiki bootstrap in headless MarcoPolo

GitHub Wiki is a separate Git repository at `OWNER/REPO.wiki.git`. Enabling the Wiki feature does not by itself create that Git repository.

Observed and documented initialization sequence:

1. Enable Wiki in repository settings.
2. Create the initial Wiki page once through the GitHub UI.
3. Only after that initial page exists does `https://github.com/OWNER/REPO.wiki.git` become cloneable and writable as a normal Git repository.

Before initialization, even an authenticated probe can return:

```text
remote: Repository not found.
fatal: repository 'https://github.com/OWNER/REPO.wiki.git/' not found
```

After the first UI page, verify existence before automation:

```bash
git ls-remote https://github.com/OWNER/REPO.wiki.git
```

### Wiki writes must use the isolated write profile

The global Git credential helper invokes the default `gh` profile unless `GH_CONFIG_DIR` is explicitly inherited by the Git process. A normal Wiki `git push` can therefore receive HTTP 403 even when the separate `gh-write` profile has repository write permission.

Use:

```bash
GH_CONFIG_DIR=/workspace/.config/gh-write git push origin master
```

A safe diagnostic is `git push --dry-run` under both profiles. In the observed 2026-08-30 case:

```text
default profile dry-run -> HTTP 403
explicit gh-write dry-run -> push plan succeeds
```

After a real Wiki push, compare local and remote commit IDs before claiming success:

```bash
local=$(git rev-parse HEAD)
remote=$(GH_CONFIG_DIR=/workspace/.config/gh-write git ls-remote origin refs/heads/master | awk '{print $1}')
test "$local" = "$remote"
```

### Preferred Wiki write wrapper

To avoid repeating Wiki credential diagnostics, use the persistent operational wrapper:

```bash
/workspace/tools/wiki-push.sh [wiki-checkout]
```

The wrapper intentionally has a narrow contract:

1. require a Git worktree whose `origin` ends in `.wiki.git`;
2. force `GH_CONFIG_DIR=/workspace/.config/gh-write`;
3. verify the write profile with `gh auth status`;
4. run a non-mutating `git push --dry-run` write probe;
5. perform the real push of the current branch;
6. read the remote branch SHA and require exact equality with local `HEAD`.

It does not create Wikis, refresh OAuth, switch credential stores, retry authentication, or fall back to the legacy GitHub wrapper. Those remain explicit recovery actions.

Machine-readable terminal states are:

```text
WIKI_PUSH SUCCESS branch=<branch> sha=<full-sha>
WIKI_PUSH BLOCKED stage=<stage> reason=<reason>
WIKI_PUSH FAILED stage=<stage> reason=<reason>
```

Acceptance test:

```bash
/workspace/tools/tests/wiki-push.sh
```

Treat these as separate postconditions:

```text
Wiki enabled
!= Wiki Git repository initialized
!= Wiki write credential selected
!= Wiki pages pushed and verified
```
