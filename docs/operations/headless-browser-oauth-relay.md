# Headless browser OAuth callback relay

Issue: [#34](https://github.com/TeaShaman-cyber/marcopolo-cookbook/issues/34)

## Problem

A CLI or MCP client running inside MarcoPolo may implement browser OAuth with a loopback callback such as:

```text
http://127.0.0.1:<port>/callback
```

The authorization page can be opened on a phone or laptop, but the provider then redirects to that device's loopback interface rather than the listener inside MarcoPolo.

This recipe relays only the browser callback back to the already-running OAuth client inside MarcoPolo. It does not replace the provider's OAuth implementation, PKCE, `state` validation, token exchange, or credential persistence.

## When to use it

Use this pattern when all of the following are true:

- the client already implements authorization-code OAuth correctly;
- the client binds its callback listener to loopback inside MarcoPolo;
- the authorization URL can be obtained without exposing long-lived credentials;
- the provider does not offer a simpler supported device-code or hosted callback flow;
- a short-lived public reverse tunnel is acceptable for the callback path.

Do not use this pattern to defeat provider authentication policy, MFA, strong-authentication requirements, or consent.

## Mechanism

```text
OAuth client in MarcoPolo
  -> loopback listener 127.0.0.1:<port>
  -> authorization URL shown to user
  -> user authenticates in external browser
  -> provider redirects browser to localhost callback
  -> user replaces only callback origin with temporary tunnel origin
  -> tunnel forwards path + query unchanged to MarcoPolo loopback listener
  -> original client validates state / completes PKCE exchange
  -> client persists its normal credential context
```

The relay transports the provider callback. The original OAuth client remains responsible for every security-critical OAuth step.

## Critical lifecycle rule

Keep the OAuth listener and reverse tunnel inside the **same managed MarcoPolo execution** until the callback completes.

A detached `nohup ... &` started by a short `workspace_shell` call is not sufficient. The MarcoPolo supervisor can terminate the process group when that execution ends, even if the child was backgrounded. A tunnel that printed a public URL is therefore not proof that the listener or tunnel is still alive later.

The safe shape is:

```sh
start_oauth_client >login.log 2>&1 &
login_pid=$!

start_reverse_tunnel_to_callback_port >tunnel.log 2>&1 &
tunnel_pid=$!

trap 'kill "$tunnel_pid" "$login_pid" 2>/dev/null || true' EXIT INT TERM
wait "$login_pid"
```

Run that shell as one managed MarcoPolo execution with a timeout long enough for the human browser step.

## Operator flow

1. Start the OAuth client inside MarcoPolo with a bounded callback timeout.
2. Make the client print the authorization URL instead of attempting to launch a browser in the headless runtime.
3. Start a temporary reverse tunnel forwarding to the exact loopback callback port.
4. Verify both the authorization URL and tunnel URL while the managed execution is still running.
5. Open the authorization URL in the external browser and complete normal provider authentication/consent.
6. When the browser redirects to the loopback callback URL, keep the entire callback path and query unchanged and replace only the origin:

```text
http://127.0.0.1:<port>/callback?<provider-query>
```

becomes:

```text
https://<temporary-tunnel-host>/callback?<same-provider-query>
```

7. Navigate to the rewritten URL. The tunnel forwards the callback to the waiting loopback listener inside MarcoPolo.
8. Shut down the tunnel after the callback has been delivered.
9. Independently verify the provider-native postcondition, such as `whoami`, connected-user status, or a harmless authenticated read.

## Security boundary

Treat the callback query as ephemeral credential material even when its authorization code is one-time and PKCE-bound.

- Never commit authorization URLs, callback URLs, codes, tokens, cookies, PKCE verifiers, auth caches, or generated credential files.
- Prefer browser-to-tunnel delivery over pasting the complete callback URL into chat or logs.
- Use a random, temporary tunnel hostname and terminate it immediately after the callback.
- Forward only the callback port required by the active OAuth client.
- Keep the provider's original `state` and PKCE validation intact; do not synthesize or modify them.
- Do not treat tunnel reachability as proof of successful login.

A success page from the callback handler proves only that the callback reached the client and passed whatever checks the handler performs before rendering that page. Credential persistence and usable provider authority require a separate readback.

## Verified Arcade example — 2026-10-28

Observed with Arcade CLI `1.16.3` inside MarcoPolo:

```text
flow                  authorization_code + PKCE S256
callback listener     127.0.0.1:9905
callback handler      validates returned state and requires code
browser launch        unsuitable in headless MarcoPolo
reverse tunnel        temporary localhost.run HTTPS origin
```

Inspection of the installed CLI confirmed that the client:

1. generates a random `state`;
2. generates a PKCE verifier and S256 challenge;
3. starts an HTTP callback server bound only to `127.0.0.1`;
4. builds the provider authorization URL using that loopback redirect URI;
5. validates returned `state` and `code`;
6. performs its own authorization-code/PKCE token exchange;
7. persists credentials only after the provider-side login flow and subsequent account checks complete.

The first relay attempt used `nohup` processes started inside a short `workspace_shell` execution. Both the Arcade listener and SSH reverse tunnel were killed when that execution ended. The public tunnel URL therefore returned no data.

The second attempt kept both processes inside one managed execution. The external browser callback reached the Arcade CLI successfully through the temporary tunnel.

### Final Arcade postcondition

Callback delivery was **VERIFIED**.

Full Arcade CLI login was **BLOCKED_STRONG_AUTH** after callback delivery because the organization required a passkey or authenticator app:

```text
Your organization requires a passkey or an authenticator app to sign in.
```

`arcade whoami` still reported not logged in, so no persistent Arcade CLI authorization is claimed from this experiment.

This distinction is intentional:

```text
callback delivered != OAuth session persisted != provider operation verified
```

## Current status of issue #34

MarcoPolo still does not expose a generic native callback relay for arbitrary remote OAuth clients in the currently observed connection surface. The original native verdict therefore remains:

```text
NOT_EXPOSED
```

What changed is the availability of a reproducible userspace fallback:

```text
USERSPACE_CALLBACK_RELAY = VERIFIED
```

Use the userspace relay only after a simpler provider-native/device-flow/MarcoPolo-native path is observed unavailable or mismatched.
