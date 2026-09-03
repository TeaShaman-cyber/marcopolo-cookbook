# GitHub wrapper — LEGACY / RECOVERY ONLY

Status: `SUPERSEDED_AS_PRIMARY_ROUTE`
Superseded: 2026-08-28

`/workspace/tools/wrapper-gh.sh` is retained for historical and recovery provenance. It is not the normal GitHub route in the current MarcoPolo workspace.

## Current route

```text
workspace_shell -> gh / git -> GitHub
```

The current route uses ordinary `gh` / `git`, but authorization is scope-separated. The default MarcoPolo OAuth profile is read-capable; explicitly authorized writes use the separate `/workspace/.config/gh-write` CLI OAuth profile via `GH_CONFIG_DIR`. After authorization or runtime changes, check the intended profile with `gh auth status`, run the smallest repository probe, and verify remote state after writes.

## When the old wrapper may be considered

Use `wrapper-gh.sh` only after the direct route is observed unavailable, fallback is actually needed, and the wrapper path is freshly re-verified. Its existence on disk is not evidence that it is current.

Do not inspect or print credential values while diagnosing either route.

## Historical provenance

Older receipts and publisher scripts may contain commands such as:

```text
/workspace/tools/wrapper-gh.sh gh repo view ...
/workspace/tools/wrapper-gh.sh git push ...
```

Treat those as historical instructions tied to the older Infisical-backed route, not as current operating guidance.

## Expanding GitHub OAuth scopes in headless MarcoPolo

The write profile is isolated at `/workspace/.config/gh-write`. Scope expansion must target this profile explicitly and must be verified after the browser/device step.

For GitHub Projects, request both read and write scopes explicitly:

```bash
GH_CONFIG_DIR=/workspace/.config/gh-write \
  gh auth refresh -h github.com -s project,read:project
```

In the headless MarcoPolo shell, `gh auth refresh` may wait for an interactive browser/TTY without returning the device code through `workspace_shell`. A working fallback is to detach the device flow and capture only its public prompt:

```bash
rm -f /tmp/gh-project-auth.out /tmp/gh-project-auth.pid
nohup sh -c "printf '\n' | GH_BROWSER=echo GH_CONFIG_DIR=/workspace/.config/gh-write gh auth refresh -h github.com -s project,read:project" \
  >/tmp/gh-project-auth.out 2>&1 </dev/null &
echo $! >/tmp/gh-project-auth.pid
sleep 1
sed -n '1,40p' /tmp/gh-project-auth.out
```

The operator opens `https://github.com/login/device` and enters the displayed one-time code.

### Important verification rule

Browser approval is not proof that the local `gh-write` credential was updated. A previous device flow was approved in the browser while the detached `gh auth refresh` process remained pending and the stored token still lacked Project scopes.

After approval, verify the local profile and the actual capability:

```bash
GH_CONFIG_DIR=/workspace/.config/gh-write gh auth status -h github.com
GH_CONFIG_DIR=/workspace/.config/gh-write gh project list --owner TeaShaman-cyber --format json
```

Only treat Project access as available after `gh auth status` shows the required Project scopes and the Project probe succeeds. If the detached flow remains pending and scopes do not change, treat it as `DEGRADED`, terminate only the exact captured auth-flow PID/process, and start a fresh device flow. Do not switch credential stores or fall back to the legacy wrapper merely because scope refresh stalled.

This follows the general runtime rule: browser authorization, stored credential state, and executable provider capability are three separate postconditions and must not be conflated.

### Observed successful Projects scope refresh — 2026-08-30

A successful headless refresh required a fresh device flow requesting both `project,read:project`. After browser approval, the detached `gh auth refresh` process exited on its own and the stored profile changed.

Observed postconditions:

```text
requested: project,read:project
gh auth status: project
project probe: gh project list -> success
```

GitHub may report only the broader `project` scope after approval; do not require the literal string `read:project` if the provider has granted `project` and the live read probe succeeds. The capability probe is authoritative for the runtime, not the textual scope list alone.

Recommended verification sequence:

```bash
GH_CONFIG_DIR=/workspace/.config/gh-write gh auth status -h github.com
GH_CONFIG_DIR=/workspace/.config/gh-write gh project list --owner TeaShaman-cyber --format json
```

Treat the refresh as successful only when the detached auth process has ended, the stored credential state has changed as expected, and the actual Project operation succeeds. Browser approval by itself is only one intermediate postcondition.

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
