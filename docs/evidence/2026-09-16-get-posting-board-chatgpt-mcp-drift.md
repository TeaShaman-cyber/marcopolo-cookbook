# Get Posting Board / ChatGPT MCP documentation drift — 2026-09-16

Status: **OBSERVED DOCUMENTATION DRIFT / PLUS DIRECT MCP LATER VERIFIED IN A NEW CONVERSATION**

This receipt records a dated mismatch between Get Posting Board's ChatGPT setup guide, OpenAI's current help documentation, and an observed ChatGPT Plus UI. It is evidence about the state observed on 2026-09-16, **not a permanent product guarantee** about future plan availability.

## Sources checked

### Get Posting Board setup guide

Source: https://getpostingboard.dev/chatgpt.md

Observed on 2026-09-16. The guide says to use ChatGPT on the web with a **Pro, Plus, Business, Enterprise or Education** account, enable Developer mode, then add a remote MCP server. It gives `https://getpostingboard.dev/mcp` as the MCP URL and OAuth scopes `board:read` plus optional `board:write`.

The same guide notes that its labels follow OpenAI documentation as read on 2026-09-15 and may vary by plan and workspace policy.

### OpenAI current help documentation

Source: https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt

Observed on 2026-09-16. The current help article states:

- full MCP, including modify/write actions, is available for **Business** and **Enterprise/Edu**;
- **Pro** users may connect MCPs with read/fetch permissions in Developer mode;
- **Plus** is not listed as a plan with custom MCP Developer mode access in that availability section or FAQ;
- MCP apps are **web only** and are not available on mobile.

Because product availability and UI can change, these statements are bound to the access date above.

## Local observation

**OBSERVATION:** during this session, a ChatGPT Plus account did not expose the documented UI path for adding a custom MCP server. This is consistent with the current OpenAI help article, but one account observation is not sufficient to establish a universal rule for every Plus account, region, rollout cohort, or future date.

## Drift

```text
Get Posting Board guide:
Plus -> Developer mode -> add remote MCP

OpenAI current help:
Business / Enterprise/Edu -> full MCP
Pro -> read/fetch MCP in Developer mode
Plus -> not listed for custom MCP Developer mode
MCP apps -> web only

Observed Plus UI:
custom MCP add path not visible
```

The safest interpretation is **documentation drift or an over-broad setup statement in the board guide**, not evidence that Get Posting Board itself is down and not proof that Plus can never receive the feature.

## Operational consequence

Do not block the board integration on ChatGPT UI availability. The MarcoPolo route remains a valid compatibility experiment:

```text
MarcoPolo
  -> pinned mcporter
  -> https://getpostingboard.dev/mcp
  -> OAuth / board identity
  -> forum-specific wrapper
  -> independent readback after writes
```

A prior unauthenticated probe already established only this much:

```text
endpoint reachable
401 OAuth challenge observed
scopes advertised: board:read board:write
```

It did **not** establish successful OAuth, tool discovery, board read access, or write access. Those remain separate future postconditions.

## Epistemic labels

- **FACT:** Get Posting Board's guide currently names Plus among plans for its Developer-mode setup path.
- **FACT:** OpenAI's current help page names Business and Enterprise/Edu for full MCP and Pro for read/fetch MCP; Plus is not named there for custom MCP access.
- **OBSERVATION:** the Plus UI inspected in this session did not expose the custom MCP path.
- **INFERENCE:** the board guide is stale or broader than the currently exposed OpenAI capability surface.
- **UNKNOWN:** whether Plus access exists for any rollout cohort not represented by the current documentation or observation.


## Resolution addendum — later on 2026-09-16

The earlier observation was not the final capability state. After the developer MCP was added through the `+` control inside ChatGPT Plugins, a **new conversation** successfully invoked the Get Posting Board developer MCP.

Operator-provided cross-chat receipt:

```text
plugin/schema exposed        = FACT
get_my_agent invoked         = COMPLETED
forum read invoked           = COMPLETED
authentication               = OAuth
connected identity           = jester-sonar
read access                  = VERIFIED
write capability advertised  = AVAILABLE
actual public write          = NOT TESTED
previous FORBIDDEN           = GONE
```

In the older conversation, the same MCP invocation had returned:

```text
FORBIDDEN: This conversation does not support developer MCPs
```

The smallest interpretation consistent with both observations is conversation-runtime staleness or capability snapshotting after plugin attachment:

```text
account can attach custom MCP
!= existing conversation runtime refreshed
!= tool invokable in that conversation

new conversation after attachment
-> tool schema exposed
-> OAuth-linked get_my_agent succeeds
-> live board read succeeds
```

This **falsifies the earlier working hypothesis that the Plus plan itself necessarily blocks custom MCP execution** for this account. It does not falsify the documentation drift: the current OpenAI help page still documents plan availability more narrowly than the capability observed here.

The direct ChatGPT route is therefore the thinnest verified route when available:

```text
ChatGPT new conversation
  -> @getpostingboard.dev
  -> OAuth-linked jester-sonar
  -> board read
```

Write remains a separate postcondition until an actual public mutation and readback are performed.

## Updated epistemic labels

- **FACT:** the older conversation exposed the app but returned `FORBIDDEN` on invocation.
- **OBSERVATION:** a new conversation created after plugin attachment successfully completed `get_my_agent` and a live forum read for `jester-sonar`.
- **INFERENCE:** developer-MCP availability can be conversation-runtime scoped or stale after attachment.
- **FACT:** advertised write capability is not the same as a verified public write.
- **UNKNOWN:** the exact OpenAI internal mechanism that caused the old/new conversation difference.


## Coexistence addendum — developer MCP versus native apps

A later cross-chat check exposed a second boundary. In the conversation where `@getpostingboard.dev` was successfully callable, invoking the normal `@GitHub` integration returned:

```text
FORBIDDEN:
This conversation is restricted to developer MCPs
```

Observed state from that conversation:

```text
@getpostingboard.dev = VERIFIED WORKING
@GitHub              = BLOCKED
reason               = conversation restricted to developer MCPs
```

This is a separate issue from Plus availability. The developer MCP itself works, but the conversation runtime appears unable to coexist with at least one ordinary integration in that state.

OpenAI's current help page says that ChatGPT can use **multiple apps** in one prompt, including OpenAI and third-party apps. The observed `restricted to developer MCPs` behavior therefore deserves its own dated drift receipt rather than being treated as intended coexistence semantics.

Source rechecked 2026-09-16:

https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt

Current interpretation:

```text
custom developer MCP usable
!= ordinary app/plugin coexistence verified
!= GitHub usable in same conversation
```

- **OBSERVATION:** Get Posting Board executed successfully in the new conversation.
- **OBSERVATION:** GitHub invocation in that conversation was rejected with `restricted to developer MCPs`.
- **FACT:** OpenAI documentation describes multiple apps as usable together.
- **INFERENCE:** the observed conversation runtime is applying a developer-MCP-only tool mode or another capability partition inconsistent with the documented coexistence model.
- **UNKNOWN:** whether this is a temporary rollout bug, a Plus-specific runtime restriction, a conversation-mode transition, or another undocumented gate.

Operationally, the direct ChatGPT route is only the thinnest route when native integrations are not also required in that same conversation. When cross-tool work needs both Get Posting Board and GitHub, preserve independent routes instead of assuming coexistence.
