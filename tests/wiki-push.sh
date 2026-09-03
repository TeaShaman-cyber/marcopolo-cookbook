#!/bin/sh
set -eu

WRAPPER=/workspace/tools/wiki-push.sh
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
BIN="$TMP/bin"
mkdir -p "$BIN" "$TMP/wiki"
LOG="$TMP/calls.log"
: > "$LOG"

cat > "$BIN/gh" <<'GH'
#!/bin/sh
set -eu
printf 'gh|GH_CONFIG_DIR=%s|%s\n' "${GH_CONFIG_DIR:-}" "$*" >> "$FAKE_LOG"
[ "${GH_CONFIG_DIR:-}" = /workspace/.config/gh-write ] || exit 91
if [ "$1 $2" = "auth status" ]; then exit 0; fi
exit 0
GH
chmod +x "$BIN/gh"

cat > "$BIN/git" <<'GIT'
#!/bin/sh
set -eu
printf 'git|GH_CONFIG_DIR=%s|%s\n' "${GH_CONFIG_DIR:-}" "$*" >> "$FAKE_LOG"
[ "${GH_CONFIG_DIR:-}" = /workspace/.config/gh-write ] || exit 92
mode=${FAKE_GIT_MODE:-success}
case "$*" in
  "-C "*" rev-parse --is-inside-work-tree") echo true ;;
  "-C "*" remote get-url origin")
    if [ "$mode" = wrong_remote ]; then
      echo https://github.com/example/project.git
    else
      echo https://github.com/example/project.wiki.git
    fi
    ;;
  "-C "*" symbolic-ref --quiet --short HEAD") echo master ;;
  "-C "*" rev-parse HEAD") echo aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa ;;
  "-C "*" push --dry-run origin master")
    [ "$mode" != dry_run_fail ] || exit 41
    ;;
  "-C "*" push origin master")
    [ "$mode" != push_fail ] || exit 42
    ;;
  "-C "*" ls-remote origin refs/heads/master")
    if [ "$mode" = mismatch ]; then
      printf '%s\trefs/heads/master\n' bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    else
      printf '%s\trefs/heads/master\n' aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    fi
    ;;
  *) echo "unexpected fake git invocation: $*" >&2; exit 99 ;;
esac
GIT
chmod +x "$BIN/git"

run_case() {
  name=$1 mode=$2 expected_rc=$3 expected_text=$4
  out="$TMP/$name.out"
  : > "$LOG"
  set +e
  FAKE_LOG="$LOG" FAKE_GIT_MODE="$mode" PATH="$BIN:$PATH" "$WRAPPER" "$TMP/wiki" >"$out" 2>&1
  rc=$?
  set -e
  if [ "$rc" -ne "$expected_rc" ]; then
    echo "FAIL $name: expected rc=$expected_rc got rc=$rc" >&2
    cat "$out" >&2
    exit 1
  fi
  grep -F "$expected_text" "$out" >/dev/null || {
    echo "FAIL $name: missing output: $expected_text" >&2
    cat "$out" >&2
    exit 1
  }
  if grep -v 'GH_CONFIG_DIR=/workspace/.config/gh-write' "$LOG" | grep -E '^(git|gh)\|' >/dev/null; then
    echo "FAIL $name: a command escaped gh-write profile" >&2
    cat "$LOG" >&2
    exit 1
  fi
  echo "ok $name"
}

run_case success success 0 'WIKI_PUSH SUCCESS branch=master sha=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
run_case wrong_remote wrong_remote 2 'WIKI_PUSH BLOCKED stage=remote reason=not_wiki_remote'
run_case dry_run_fail dry_run_fail 3 'WIKI_PUSH BLOCKED stage=preflight reason=write_probe_failed'
run_case push_fail push_fail 4 'WIKI_PUSH FAILED stage=push reason=git_push_failed'
run_case mismatch mismatch 5 'WIKI_PUSH FAILED stage=readback reason=sha_mismatch'

echo 'wiki-push acceptance: PASS'
