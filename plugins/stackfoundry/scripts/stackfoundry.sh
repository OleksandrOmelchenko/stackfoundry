#!/bin/sh
# stackfoundry helper CLI launcher. Finds Python >= 3.11 and runs the CLI isolated (-I: no user site, no env
# overrides, no script directory on sys.path), so a planted module in the user's repo is never imported.
# Usage: sh <plugin root>/scripts/stackfoundry.sh <subcommand> [args]   (--help lists them)
# Windows without sh: pwsh -NoProfile -File <plugin root>/scripts/stackfoundry.ps1 <subcommand> [args]

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
cli="$here/stackfoundry/cli.py"

ok() {
  "$@" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1
}

# The absolute path of a program on PATH, or nothing. A relative PATH entry (`.`, or an empty one) would find a
# copy planted in the repo the hook runs in; git is resolved the same way (scripts/stackfoundry/gitutil.py git_exe).
# PATH is walked by hand: `command -v` in bash turns a relative entry into an absolute path under the current folder.
abspath() {
  old_ifs=$IFS
  IFS=:
  set -f
  for dir in $PATH; do
    case "$dir" in
      /*|[A-Za-z]:[\\/]*)
        if [ -f "$dir/$1" ] && [ -x "$dir/$1" ]; then
          IFS=$old_ifs; set +f
          printf '%s\n' "$dir/$1"
          return 0
        fi ;;
    esac
  done
  IFS=$old_ifs; set +f
  return 1
}

for name in python3 python; do
  if p=$(abspath "$name") && ok "$p"; then
    exec "$p" -I "$cli" "$@"
  fi
done
if p=$(abspath py) && ok "$p" -3; then
  exec "$p" -3 -I "$cli" "$@"
fi

echo "stackfoundry: Python 3.11 or newer is required (tried python3, python, py -3 at absolute paths on PATH)." >&2
# As a hook, a missing Python must never block the session: exit 0 with no opinion. Cursor blocks on empty output,
# so it gets an explicit allow; the CLI's own callers see the message and 127.
if [ "${1:-}" = "guard" ]; then
  case " $* " in *" cursor "*|*"--client=cursor"*) echo '{"permission": "allow"}' ;; esac
  exit 0
fi
exit 127
