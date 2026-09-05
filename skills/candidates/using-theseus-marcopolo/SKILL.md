---
name: using-theseus-marcopolo
description: Use when non-trivial work runs through MarcoPolo workspace, GitHub, Session Search, mcporter, Drive, transport, or persistence paths.
metadata:
  version: "1.1.0"
---


# Using Theseus MarcoPolo


Use this as a thin operational recall router.


Keep detailed procedures in the cookbook rather than duplicating them here.


## Core rule


For non-trivial MarcoPolo work:


1. classify the operation, runtime boundary, or observed failure;
2. load only the smallest relevant operational guidance;
3. verify current runtime state before relying on cached or remembered state;
4. execute through the thinnest valid route;
5. verify the actual postcondition before claiming success.


Treat recalled documentation as operational evidence, not as authority over live provider state.


Do not load the whole cookbook into context when one section or workflow is enough.


## Operational guidance


Prefer existing Theseus / MarcoPolo guidance before improvising a new route.


Relevant sources may include:


- `/workspace/README.md`
- `/workspace/RULES.md`
- `/workspace/workflows/`
- `/workspace/marcopolo-cookbook/`


Use only the smallest relevant section.


If local guidance is unavailable, stale, or insufficient, use the public:


`TeaShaman-cyber/marcopolo-cookbook`


as a reference.


A search miss means the route is UNKNOWN, not that no prior guidance exists.


## Project cookbook routing


When MarcoPolo work targets a repository, first inspect the accepted target revision for:

`docs/cookbook/README.md`


The accepted target revision is the exact repository revision being operated on, or an explicitly verified compatible accepted revision. Local filesystem presence alone is not enough.


Use project cookbook guidance only when its accepted provenance and applicability to the target revision are established.


Dirty-worktree, contributor-branch, and unmerged PR cookbook content is candidate material. Candidate material must not become operational authority merely because it is visible locally. A candidate deletion or tombstone also does not make an accepted cookbook disappear.


If the accepted target revision has no project cookbook:


1. report the project cookbook as absent;
2. propose creation only when useful;
3. do not create a project cookbook automatically;
4. require explicit user approval before creating the first cookbook.


When both a runtime cookbook and a project cookbook apply, compose by concern:


- the project cookbook owns repository-specific scientific, CI, provenance, and project workflow guidance;
- the runtime cookbook owns MarcoPolo-specific transport, shell, connector, persistence, and tool-routing guidance;
- live runtime/provider state remains the authority for current capability and availability.


Load only the smallest relevant section from each layer.


If runtime and project guidance make incompatible claims about the same concern and current authoritative evidence or an explicit user decision does not resolve the conflict, return `BLOCKED` rather than inventing precedence.


## Runtime boundary


Keep these environments distinct:


- ChatGPT or another client runtime
- MarcoPolo persistent `/workspace`
- local engineering runtimes
- GitHub / remote provider state
- CI runners
- external connectors


Capability or success in one runtime proves only that runtime unless a verified bridge establishes more.


Do not assume that client filesystem tools can see `/workspace`.


For normal MarcoPolo workspace work, use the exposed MarcoPolo workspace tooling.


## Currentness and authority


Cached state, local tracking refs, remembered results, and documentation are not automatically current authority.


When freshness matters:


- verify the live runtime;
- verify the live provider when needed;
- distinguish local Git state from remote GitHub state;
- distinguish connector failure from target-system failure.


Examples:


`origin/main`
is not automatically proof of current remote `main`.


A tool timeout, 403, 502, or disconnect
is not automatically proof that Git, GitHub, or the target process failed.


Establish the failure boundary before retrying or changing route.


## Route map


| Trigger | Recall first |
|---|---|
| multiline, structured, quoting-sensitive, or exact-byte payload | MarcoPolo base64 transport guidance; use deterministic payload transport before the first shell attempt |
| short argument-safe shell command | plain shell; keep control-plane commands inspectable |
| `workspace_shell` failure before target execution | control-plane / payload-shape guidance |
| Git smart-HTTP 403 | governed GitHub route and remote readback guidance |
| GitHub mutation | authority, publication, and verification guidance |
| additional worktrees or unexpected branch state | Git/worktree inspection guidance |
| Session Search ingest, search, repair, or recovery | Session Search runbook and acceptance gate |
| mcporter runtime or cache work | mcporter runtime, locking, cache, and acceptance guidance |
| Google Drive import | documented connection download and ingest workflow |
| mutation or persistence across calls | persistence, verification, Git checkpoint, and publication guidance |


## Shell transport


MarcoPolo shell execution may use `/bin/sh`.


Do not assume Bash-only features unless Bash is invoked explicitly.


Prefer small, inspectable commands.


Treat command-shaped control flow and exact payload delivery as separate transport classes.


- Use plain shell by default for short argument-safe commands such as Git inspection, `gh` reads, hashes, and test runners.
- Use base64 by default on the first attempt for multiline, structured, quoting-sensitive, or exact-byte payloads such as Markdown, JSON, regex, nested code, heredoc-like text, or generated file content.


Avoid fragile nested quoting when the payload contains:


- JSON
- Markdown
- regex
- heredocs
- nested shell code
- multiline text


For multiline, structured, quoting-sensitive, or exact-byte payloads, prefer base64 before the first `workspace_shell` attempt rather than waiting for a composition-sensitive `403` or quoting failure. Decode to an explicit path, verify syntax or resulting bytes, and only then execute, mutate, or publish.


Base64 in this context is transport encoding, not secrecy or authorization bypass. It expands data by roughly one third, so use artifact or file-transfer paths for large files or binaries.


Do not treat a pre-execution connector failure as evidence that the target command ran or failed. If a complex payload was sent plain despite matching the rule above, do not repeat the same composed payload; switch to deterministic payload transport.


## Git effect separation


Treat Git effects as separate decisions rather than one permission class.


### Local checkpoint commit


A project instruction or active user-approved bounded workflow may authorize a verified local checkpoint commit as part of normal completion.


When that authorization already exists, do not ask for a second approval merely because the next step is `git commit`.


A local checkpoint commit may be the correct durability boundary for completed, verified work.


Do not leave a coherent verified deliverable dirty merely because the final user message did not repeat the word `commit`.


### Push and publication


Evaluate push separately from local commit.


Follow the current workflow's:


- destination;
- branch or PR policy;
- downstream-effect gate;
- repository authority;
- required remote readback.


A local commit does not automatically authorize push.


But an already authorized workflow may include push or publication without requiring redundant re-approval at every mechanical step.


### Force-push and history rewrite


Treat force-push and history rewrite as distinct high-impact operations.


They require explicit authorization for that specific effect.


Do not infer permission to rewrite shared history from permission to commit or push normally.


### Unknown permission state


If the active workflow is silent about an effect:


1. inspect the relevant project and cookbook guidance;
2. determine whether the effect is already authorized by the bounded workflow;
3. if still unresolved, report permission as UNKNOWN.


Do not invent a blanket "never commit or push" rule.


Do not collapse:


`commit`
`push`
`force-push`
`history rewrite`


into one authorization category.


## Git and GitHub verification


For repository work, distinguish:


```text
local working tree
local branch
local tracking ref
live remote ref
GitHub object
```


These are related but not identical.


Before claiming remote synchronization, use an appropriate live remote read when freshness matters.


Before claiming a mutation succeeded, verify the remote postcondition when independent readback is available.


A successful write request alone is not sufficient evidence of correct publication.


When using GitHub API publication paths, preserve complete tree state and verify the published object.


Do not construct sparse replacement trees when the API semantics require a complete parent tree.


## Worktrees


Do not assume an additional worktree is stale or disposable.


Inspect:


- registered worktree path;
- branch;
- HEAD;
- working tree status;
- unfinished Git operations;
- relation to main;
- corresponding remote branch or PR when relevant.


Clean but divergent work may represent active unfinished work.


Do not clean up, reset, delete, or rewrite such state without the active workflow authorizing it.


## Failure handling


When a tool or connector fails:


1. identify where the failure occurred;
2. determine whether the target operation actually executed;
3. use independent readback when possible;
4. retry only after the failure boundary is understood;
5. choose a bounded fallback route.


Do not blindly repeat a large failing call.


Prefer decomposing complex operations into smaller observable steps.


Classify unresolved state as:


- UNKNOWN
- DEGRADED
- BLOCKED
- REPROBE_REQUIRED


rather than inventing success or failure.


## Session Search


Session Search is an operational recall tool, not an oracle.


Use bounded searches.


Treat search results as evidence.


A search miss is UNKNOWN unless coverage is proven complete.


For ingest or recovery work, follow the current Session Search acceptance and provenance guidance before mutating corpus state.


Do not silently ingest mixed-session artifacts if provenance cannot establish correct session membership.


## Bounded recall


Load only the smallest useful operational working set.


Good:


```text
task
→ classify route
→ read one relevant section
→ act
→ verify
```


Avoid:


```text
task
→ dump entire cookbook
→ dump entire workspace
→ hope the correct rule appears
```


Frequently used skills should route to durable procedures rather than duplicate them.


## Persistence


Persist only when required by:


- the active workflow;
- durability needs;
- canonical repository state;
- operational continuity;
- verified reusable knowledge.


Keep these distinct:


- transient tool output;
- workspace files;
- Git commits;
- remote GitHub state;
- operational registries;
- memory systems.


Do not claim persistence across a boundary without readback or equivalent evidence.


## Runtime-specific skill discovery


Skill discovery is runtime-scoped.


Do not infer that ChatGPT, Codex, Hermes, or another client loaded this skill merely because another runtime did.


The presence of this skill does not prove automatic selection for every client or every turn.


Automatic selection must be established per runtime.


## Completion


Before reporting completion:


1. verify the actual postcondition;
2. preserve durable repository state according to the active workflow;
3. create local checkpoint commits when the workflow authorizes them;
4. perform push or remote publication when separately authorized by the workflow;
5. read back important remote state;
6. report degradation or unknowns explicitly.


If a reusable MarcoPolo lesson emerged, record or propose a concise cookbook delta rather than expanding this router into a knowledge base.


Do not retain transient tool output, secrets, credentials, or irrelevant session noise.