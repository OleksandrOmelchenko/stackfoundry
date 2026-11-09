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

if ok python3; then
  exec python3 -I "$cli" "$@"
elif ok python; then
  exec python -I "$cli" "$@"
elif ok py -3; then
  exec py -3 -I "$cli" "$@"
fi

echo "stackfoundry: Python 3.11 or newer is required (tried python3, python, py -3)." >&2
# As a hook, a missing Python must never block the session: exit 0 with no opinion. Cursor blocks on empty output,
# so it gets an explicit allow; the CLI's own callers see the message and 127.
if [ "${1:-}" = "guard" ]; then
  case " $* " in *" cursor "*|*"--client=cursor"*) echo '{"permission": "allow"}' ;; esac
  exit 0
fi
exit 127
