#!/usr/bin/env bash
set -euo pipefail

if ! command -v rg >/dev/null 2>&1; then
  echo 'BLOCKED: rg unavailable' >&2
  exit 69
fi

usage() {
  cat <<'USAGE'
Usage: search.sh [options] PATTERN [PATH ...]

Options:
  --regex           Treat PATTERN as a regular expression.
  -C, --context N   Show N lines of context around each match.
  -g, --glob GLOB   Include/exclude files using an rg glob. Repeatable.
  --hidden          Search hidden files, but never .git/.
  --json            Emit ripgrep JSON Lines output.
  -h, --help        Show this help.

Default behavior uses fixed-string matching, line numbers, filenames,
Unicode-aware ripgrep matching, and no ANSI color output.
USAGE
}

mode=fixed
context=''
hidden=0
json=0
globs=()

while (($#)); do
  case "$1" in
    --regex)
      mode=regex
      shift
      ;;
    -C|--context)
      if (($# < 2)); then
        echo 'ERROR: --context requires a non-negative integer' >&2
        exit 64
      fi
      context=$2
      if [[ ! $context =~ ^[0-9]+$ ]]; then
        echo 'ERROR: --context requires a non-negative integer' >&2
        exit 64
      fi
      shift 2
      ;;
    -g|--glob)
      if (($# < 2)); then
        echo 'ERROR: --glob requires a pattern' >&2
        exit 64
      fi
      globs+=("$2")
      shift 2
      ;;
    --hidden)
      hidden=1
      shift
      ;;
    --json)
      json=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "ERROR: unknown option: $1" >&2
      usage >&2
      exit 64
      ;;
    *)
      break
      ;;
  esac
done

if (($# < 1)); then
  echo 'ERROR: PATTERN is required' >&2
  usage >&2
  exit 64
fi

pattern=$1
shift
if (($# == 0)); then
  set -- .
fi

args=(--color never --line-number --with-filename)
if [[ $mode == fixed ]]; then
  args+=(--fixed-strings)
fi
if [[ -n $context ]]; then
  args+=(--context "$context")
fi
if ((hidden)); then
  args+=(--hidden --glob '!**/.git/**')
fi
for glob in "${globs[@]}"; do
  args+=(--glob "$glob")
done
if ((json)); then
  args+=(--json)
fi

exec rg "${args[@]}" -- "$pattern" "$@"
