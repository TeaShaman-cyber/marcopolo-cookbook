#!/bin/sh
set -eu

CFG=/workspace/.config/infisical/universal-auth.env
BIN=/workspace/.local/bin/infisical
DOMAIN=https://138-68-80-121.sslip.io
PROJECT_ID=fde54488-4dfa-4b3a-adcd-e901f7cfaf2f
ENV_SLUG=prod
SECRET_PATH=/providers

[ -r "$CFG" ] || { echo '{"status":"BLOCKED","reason":"auth_file_missing"}'; exit 2; }

set -a
. "$CFG"
set +a

: "${INFISICAL_CLIENT_ID:?missing INFISICAL_CLIENT_ID}"
: "${INFISICAL_CLIENT_SECRET:?missing INFISICAL_CLIENT_SECRET}"

ACCESS_TOKEN="$($BIN login --method=universal-auth --client-id "$INFISICAL_CLIENT_ID" --client-secret "$INFISICAL_CLIENT_SECRET" --domain "$DOMAIN" --plain --silent)"
[ -n "$ACCESS_TOKEN" ] || { echo '{"status":"BLOCKED","reason":"empty_access_token"}'; exit 2; }

unset INFISICAL_CLIENT_ID INFISICAL_CLIENT_SECRET
INFISICAL_TOKEN="$ACCESS_TOKEN" exec "$BIN" run --projectId "$PROJECT_ID" --env "$ENV_SLUG" --path "$SECRET_PATH" --domain "$DOMAIN" -- "$@"
