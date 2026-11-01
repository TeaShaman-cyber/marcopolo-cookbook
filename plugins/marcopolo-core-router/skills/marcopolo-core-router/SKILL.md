---
name: marcopolo-core-router
description: Use when work involves MarcoPolo authority or credentialed connection setup, workspace state, GitHub route selection across runtimes, repository currentness, 403 failures, or verified persistence/completion.
---

# MarcoPolo Core Router

Use this skill as a thin operational guardrail, not as a replacement for the cookbook.
## Authority precedence
The Project Contract remains authoritative for routing, authority, permission, and change control. This project-specific routing skill operates under that contract; vendor/plugin skills are mechanics guidance only and must not override it or this skill on routing, authority, or permission. "Read this first" is invocation guidance, not project-policy precedence.
## Fast path
1. Identify the authority domain and runtime boundary before choosing a tool.
2. Use the thinnest valid route that preserves freshness, permission, verification, and required durability.
3. Load only the smallest relevant section of current operational guidance.
4. Treat capability != permission.
5. Treat cached or visible state as evidence, not current authority.
6. Claim success only after an observable postcondition appropriate to the authority domain.

## MarcoPolo currentness

When work depends on /workspace state:

- read /workspace/RULES.md for current runtime mechanics;
- do not treat a visible checkout, branch, or cached origin ref as current authority merely because it exists;
- when freshness matters, verify the selected authoritative ref or provider state;
- never reset, switch, or destroy a dirty or active worktree just to obtain a clean view;
- prefer reading the authoritative ref directly or using an isolated clean worktree.

For deeper shell, transport, connector, or recovery detail, load only the needed section from:

/workspace/marcopolo-cookbook/marcopolo/README.md

## Managed credential connections

For user-owned APIs, databases, storage, or other credentialed integrations:

- check the current `connection_setup` / connection catalog before inventing plaintext files, ad-hoc vaults, or custom secret plumbing;
- a credentialed MarcoPolo connection can provide a privileged credential boundary: browser setup captures authentication outside the workspace/model path and the connector uses stored credentials for its advertised operations;
- that boundary is capability-scoped: it does not imply secret injection into an arbitrary local subprocess or support for an unregistered provider type; treat those paths as UNKNOWN until exposed and verified;
- verify the resulting connection with current list/test/capability readback, and inspect returned data for accidental credential reflection; privileged storage does not guarantee that an upstream response will redact authentication material;
- if no canonical connection type exists, do not fall back to model-visible plaintext merely to make the integration work; choose another authorized provider-native authentication route or report the capability gap.

## Cross-runtime file bridge

When an artifact must move between isolated runtimes:

- prefer a directly available native file/reference bridge first;
- if both MarcoPolo and the destination runtime have authorized Google Drive access, prefer Google Drive as the standard bridge instead of model-visible base64 chunking;
- before upload, record source size and a cryptographic hash when practical;
- upload through the governed MarcoPolo Drive connection, then use the exact returned Drive file ID on the destination side;
- fetch or materialize raw bytes/file_uri there and verify size/hash before consequential use;
- treat the Drive ID or connector file reference as transport evidence, not authority over the artifact's meaning or destination action;
- keep temporary bridge artifacts private and remove them only when cleanup is authorized;
- use base64 chunking only after the native/Drive bridge is observed unavailable, blocked, unsuitable, or mismatched.

Do not assume a working connector in one runtime implies the same connector or authority in another. Verify both sides independently.

## GitHub routing

Choose the route by required capability and authority:

- bounded current-state read with no workspace-local processing: native GitHub read is valid when available;
- work depending on workspace files, local processing, durable artifacts, or MarcoPolo-managed state: prefer MarcoPolo;
- before the first GitHub mutation in a reconstructed or changed runtime, verify `gh-write` with `/workspace/marcopolo-cookbook/github-write-preflight.sh --check`; if it reports BLOCKED, stop before mutation and repair bootstrap rather than discovering the missing write profile through a failed push;
- mutation: require current authorization, use the governed write route, and perform exact remote readback;
- capability-specific surfaces such as Projects must be probed directly rather than inferred from ordinary repository access;
- visibility != existence: if one connector, installation, credential, or profile cannot resolve a repository or GitHub object, treat that result as UNKNOWN for existence until an appropriate authorized profile or authoritative surface confirms absence.

Do not infer write authority from a successful read. Do not infer repository absence from profile-scoped invisibility.

## GitHub Projects coordination

Treat GitHub Projects as a coordination projection, not authority or permission.

- when durable project-owned work has a dedicated Project, keep the coordinating Issue in the narrowest owning repository/lab Project;
- synchronize Project lifecycle fields from verified Issue/PR disposition, never the reverse;
- do not require every implementation PR as a separate Project item when the coordinating Issue already carries the work;
- probe Projects as a separate capability surface; ordinary repository access does not prove Projects access;
- if a Projects-specific connector is unauthorized while ordinary GitHub access works, keep those authority surfaces separate rather than replacing or reusing credentials blindly;
- if Projects is unavailable, continue authorized canonical repository work and report Project synchronization DEGRADED rather than blocking unrelated repo work;
- when the project-centric item list may be stale, verify membership through reverse issue/PR projectItems or the repository verifier before attempting repair;
- authorized Project mutations require Project readback.

## 403 rule

A 403 is a routing signal, not a diagnosis: `CALL_BLOCKED / ROUTE_HEALTH_UNKNOWN`; never declare the route UNAVAILABLE from one 403.

After a MarcoPolo `workspace_shell` control-plane rejection, MUST:
1. Establish whether target execution occurred. If a mutation may have run, check its postcondition before any retry; a read-only canary never proves target success.
2. Reprobe with neutral `workspace_shell("date")` (or `pwd`): max 2 small read-only probes, not the same rejected payload. If blocked, report `DEGRADED / REPROBE_REQUIRED / ROUTE_HEALTH_UNKNOWN`, not a dead route.
3. If the canary succeeds, report `ROUTE_AVAILABLE / CALL_BLOCKED`; original command remains unverified. Retry needed work with a smaller or normalized payload; do not repeat the same failing payload unchanged.
4. Allow fallback only after observed route/capability insufficiency or blocked neutral probes, preserving authority, permissions, and exact readback. Do not promote a guessed outage into a fact.

If Git or GitHub returns 403: identify the credential/profile and required capability; separate provider authorization from transport rejection, and verify the write postcondition before retry. A read-profile failure does not prove repository absence.

## Verification and persistence

Keep these states separate:

local working tree -> local branch -> tracking ref -> live remote ref -> GitHub object

A successful executor response is not enough when independent verification is available.

Persist only when required by the active workflow, canonical record, or continuity need. Important writes require readback or equivalent confirmation.

If required evidence cannot be established, report BLOCKED, DEGRADED, UNKNOWN, or REPROBE_REQUIRED rather than inventing success.

## Scope

This skill intentionally contains only recurring routing invariants.

Detailed procedures, rare failures, historical evidence, and recovery steps remain in the cookbook. If more detail is needed, retrieve the smallest relevant section and stop there.
