#!/bin/sh
set -eu
CFG=/workspace/.config/infisical/universal-auth.env
BIN=/workspace/.local/bin/infisical
DOMAIN=https://138-68-80-121.sslip.io
PROJECT=fde54488-4dfa-4b3a-adcd-e901f7cfaf2f
[ -r "$CFG" ] || { echo PROJECT_FAIL; exit 10; }
. "$CFG"
T="$($BIN login --method=universal-auth --client-id="$INFISICAL_CLIENT_ID" --client-secret="$INFISICAL_CLIENT_SECRET" --domain="$DOMAIN" --silent --plain 2>/dev/null)" || { echo PROJECT_FAIL; exit 20; }
unset INFISICAL_CLIENT_ID INFISICAL_CLIENT_SECRET
$BIN secrets folders get --projectId="$PROJECT" --token="$T" --domain="$DOMAIN" --path=/ --output=json --silent >/dev/null 2>&1 || { unset T; echo PROJECT_FAIL; exit 30; }
unset T
printf '%s\n' PROJECT_OK
printf '%s\n' metadata_probe=yes
printf '%s\n' secret_output=no
