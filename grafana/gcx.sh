#!/bin/sh
set -eu
umask 077

SOURCE_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
RUNTIME_DIR=${GCX_RUNTIME_DIR:-/workspace/tools/gcx}
RELEASE=1.7.1
ARCHIVE="$RUNTIME_DIR/runtime/gcx_${RELEASE}_linux_amd64.tar.gz"
BINARY="$RUNTIME_DIR/bin/gcx"
HELPER="$RUNTIME_DIR/gcx-oauth-relay.sh"
ARCHIVE_SHA=5f1601feac13d850017064a9b556f11983de6def2986ba0bee402a947659c3e9
BINARY_SHA=8ffc2438e22e9010d2158ee38ab3bfc749e71d7c3f7641cedeb822e117b36aaa

fail() {
	echo "GCX_RUNTIME BLOCKED: $1" >&2
	exit 2
}

verify_digest() {
	expected=$1
	file=$2
	[ -f "$file" ] && [ ! -L "$file" ] || fail "missing_or_linked_artifact"
	printf '%s  %s\n' "$expected" "$file" | sha256sum -c - >/dev/null 2>&1 || fail "checksum_mismatch"
}

verify_runtime() {
	[ -x "$BINARY" ] && [ ! -L "$BINARY" ] || fail "binary_missing"
	verify_digest "$BINARY_SHA" "$BINARY"
	[ -f "$HELPER" ] && [ ! -L "$HELPER" ] || fail "helper_missing"
	cmp -s "$SOURCE_DIR/gcx-oauth-relay.sh" "$HELPER" || fail "helper_projection_stale"
	echo "GCX_RUNTIME VERIFIED version=$RELEASE binary=sha256 helper=source_matched"
}

case "${1:---help}" in
--download)
	mkdir -p "$RUNTIME_DIR/runtime"
	stage=$(mktemp "$RUNTIME_DIR/runtime/.gcx-archive-XXXXXX")
	trap 'rm -f "$stage"' EXIT HUP INT TERM
	curl --fail --location --silent --show-error --retry 2 \
		"https://github.com/grafana/gcx/releases/download/v${RELEASE}/gcx_${RELEASE}_linux_amd64.tar.gz" \
		-o "$stage"
	verify_digest "$ARCHIVE_SHA" "$stage"
	mv -f "$stage" "$ARCHIVE"
	trap - EXIT HUP INT TERM
	echo "GCX_RUNTIME ARCHIVE_VERIFIED"
	;;
--install)
	verify_digest "$ARCHIVE_SHA" "$ARCHIVE"
	mkdir -p "$RUNTIME_DIR/bin"
	stage=$(mktemp "$RUNTIME_DIR/bin/.gcx-binary-XXXXXX")
	trap 'rm -f "$stage"' EXIT HUP INT TERM
	tar -xOzf "$ARCHIVE" gcx >"$stage" || fail "archive_extract_failed"
	verify_digest "$BINARY_SHA" "$stage"
	chmod 755 "$stage"
	mv -f "$stage" "$BINARY"
	trap - EXIT HUP INT TERM
	install -m 700 "$SOURCE_DIR/gcx-oauth-relay.sh" "$HELPER"
	verify_runtime
	;;
--check)
	verify_runtime
	;;
--help)
	echo "usage: gcx.sh --download | --install | --check | <gcx arguments>"
	echo "explicit download and installation; routine commands do not download"
	;;
*)
	[ -x "$BINARY" ] || fail "binary_missing"
	exec "$BINARY" "$@"
	;;
esac
