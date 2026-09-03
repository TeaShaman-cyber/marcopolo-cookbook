#!/bin/sh
set -eu
CFG=/workspace/.config/infisical/universal-auth.env
BIN=/workspace/.local/bin/infisical
DOMAIN=https://138-68-80-121.sslip.io
[ -r "$CFG" ] || { echo ACCESS_FAIL; exit 10; }
. "$CFG"
T="$($BIN login --method=universal-auth --client-id="$INFISICAL_CLIENT_ID" --client-secret="$INFISICAL_CLIENT_SECRET" --domain="$DOMAIN" --silent --plain 2>/dev/null)" || { echo ACCESS_FAIL; exit 20; }
[ -n "$T" ] || { echo ACCESS_FAIL; exit 21; }
unset INFISICAL_CLIENT_ID INFISICAL_CLIENT_SECRET
printf '%s\n' ACCESS_OK
printf '%s\n' token_received=yes
printf '%s\n' secret_output=no
unset T
