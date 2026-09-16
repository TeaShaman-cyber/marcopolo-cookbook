# Get Posting Board / ChatGPT MCP documentation drift — 2026-09-16

Status: **OBSERVED DOCUMENTATION DRIFT / CAPABILITY NOT VERIFIED ON PLUS**

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
