---
name: marcopolo-core-router
description: Use when work involves MarcoPolo workspace state, GitHub route selection across runtimes, repository currentness, 403 failures, or verified persistence/completion.
---

# MarcoPolo Core Router

Use this skill as a thin operational guardrail, not as a replacement for the cookbook.

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

## GitHub routing

Choose the route by required capability and authority:

- bounded current-state read with no workspace-local processing: native GitHub read is valid when available;
- work depending on workspace files, local processing, durable artifacts, or MarcoPolo-managed state: prefer MarcoPolo;
- mutation: require current authorization, use the governed write route, and perform exact remote readback;
- capability-specific surfaces such as Projects must be probed directly rather than inferred from ordinary repository access.

Do not infer write authority from a successful read.

## 403 rule

A 403 is a routing signal, not a diagnosis.

If a MarcoPolo/control-plane rejection happens before target execution:

- do not claim that the target command ran or failed;
- verify the target postcondition first;
- if the payload is multiline, structured, or quoting-sensitive, normalize transport before retrying;
- do not repeat the same failing payload unchanged.

If Git or GitHub returns 403:

- identify the credential/profile and required capability;
- distinguish provider capability from repository permission;
- switch route only after the failure boundary is understood;
- after any authorized mutation, perform exact remote readback.

If the boundary remains unresolved, report DEGRADED or UNKNOWN instead of guessing.

## Verification and persistence

Keep these states separate:

local working tree -> local branch -> tracking ref -> live remote ref -> GitHub object

A successful executor response is not enough when independent verification is available.

Persist only when required by the active workflow, canonical record, or continuity need. Important writes require readback or equivalent confirmation.

If required evidence cannot be established, report BLOCKED, DEGRADED, UNKNOWN, or REPROBE_REQUIRED rather than inventing success.

## Scope

This skill intentionally contains only recurring routing invariants.

Detailed procedures, rare failures, historical evidence, and recovery steps remain in the cookbook. If more detail is needed, retrieve the smallest relevant section and stop there.
