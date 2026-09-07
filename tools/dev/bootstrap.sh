#!/bin/sh
set -eu

DEST=${THESEUS_DEV_BIN:-/workspace/.local/theseus-dev/bin}
MICRO_VERSION=2.0.15
RUFF_VERSION=0.16.6
SHELLCHECK_VERSION=0.11.0
SHFMT_VERSION=3.14.0

fail() {
	printf 'dev-bootstrap: %s\n' "$*" >&2
	exit 1
}

check_versions() {
	[ -x "$DEST/micro" ] || fail "missing $DEST/micro"
	[ -x "$DEST/ruff" ] || fail "missing $DEST/ruff"
	[ -x "$DEST/shellcheck" ] || fail "missing $DEST/shellcheck"
	[ -x "$DEST/shfmt" ] || fail "missing $DEST/shfmt"

	micro_v=$($DEST/micro -version | awk '/^Version:/ {print $2; exit}')
	ruff_v=$($DEST/ruff --version | awk '{print $2; exit}')
	shellcheck_v=$($DEST/shellcheck --version | awk '/^version:/ {print $2; exit}')
	shfmt_v=$($DEST/shfmt --version | sed 's/^v//')

	[ "$micro_v" = "$MICRO_VERSION" ] || fail "micro version $micro_v != $MICRO_VERSION"
	[ "$ruff_v" = "$RUFF_VERSION" ] || fail "ruff version $ruff_v != $RUFF_VERSION"
	[ "$shellcheck_v" = "$SHELLCHECK_VERSION" ] || fail "shellcheck version $shellcheck_v != $SHELLCHECK_VERSION"
	[ "$shfmt_v" = "$SHFMT_VERSION" ] || fail "shfmt version $shfmt_v != $SHFMT_VERSION"

	printf 'micro %s\nruff %s\nshellcheck %s\nshfmt %s\n' "$micro_v" "$ruff_v" "$shellcheck_v" "$shfmt_v"
}

case ${1:-} in
--check)
	check_versions
	exit 0
	;;
--install | '')
	;;
*)
	fail "usage: $0 [--install|--check]"
	;;
esac

[ "$(uname -s)" = Linux ] || fail "only Linux is supported by this bootstrap"
[ "$(uname -m)" = x86_64 ] || fail "only Linux x86_64 is supported by this bootstrap"

TMP=${TMPDIR:-/tmp}/theseus-dev-bootstrap.$$
mkdir -p "$DEST" "$TMP"
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

download() {
	url=$1
	digest=$2
	target=$3
	curl -fL --retry 2 -o "$target" "$url"
	printf '%s  %s\n' "$digest" "$target" | sha256sum -c -
}

download \
	"https://github.com/micro-editor/micro/releases/download/v${MICRO_VERSION}/micro-${MICRO_VERSION}-linux64-static.tar.gz" \
	267d238eac1e26ed053d13d4d48bd421b87f9eb538b604f0b2f74a85598b6cc2 \
	"$TMP/micro.tgz"
tar -xzf "$TMP/micro.tgz" -C "$TMP"
cp "$TMP/micro-${MICRO_VERSION}/micro" "$DEST/micro"

download \
	"https://github.com/astral-sh/ruff/releases/download/${RUFF_VERSION}/ruff-x86_64-unknown-linux-gnu.tar.gz" \
	0696335ef16615d8c7445ad438750eb0f55b3da6f153df21265a7c6d5750254f \
	"$TMP/ruff.tgz"
tar -xzf "$TMP/ruff.tgz" -C "$TMP"
cp "$TMP/ruff-x86_64-unknown-linux-gnu/ruff" "$DEST/ruff"

download \
	"https://github.com/koalaman/shellcheck/releases/download/v${SHELLCHECK_VERSION}/shellcheck-v${SHELLCHECK_VERSION}.linux.x86_64.tar.gz" \
	b7af85e41cc99489dcc21d66c6d5f3685138f06d34651e6d34b42ec6d54fe6f6 \
	"$TMP/shellcheck.tgz"
tar -xzf "$TMP/shellcheck.tgz" -C "$TMP"
cp "$TMP/shellcheck-v${SHELLCHECK_VERSION}/shellcheck" "$DEST/shellcheck"

download \
	"https://github.com/mvdan/sh/releases/download/v${SHFMT_VERSION}/shfmt_v${SHFMT_VERSION}_linux_amd64" \
	fe42021c7272ef2d67ea36cbc3031683c625d0badec733ef3a57b567246a0b66 \
	"$TMP/shfmt"
cp "$TMP/shfmt" "$DEST/shfmt"

chmod 0755 "$DEST/micro" "$DEST/ruff" "$DEST/shellcheck" "$DEST/shfmt"
check_versions
