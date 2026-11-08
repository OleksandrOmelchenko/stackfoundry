#!/bin/sh
# Copy a fixture into the current (empty) eval workspace and commit it, so diffs and history work.
# Usage from plugins/stackfoundry/evals/<case>/scaffold.sh:
#   SCAFFOLD_LIB="$(dirname "$0")/../../../../fixtures/scaffold-lib.sh"; . "$SCAFFOLD_LIB"; scaffold <fixture>
set -eu

copy_tree() {
  # Copy every file of $1 into the current directory, except the answer key.
  (cd "$1" && find . -type f ! -name EXPECTED.md) | while IFS= read -r f; do
    mkdir -p "$(dirname "$f")"
    cp "$1/$f" "$f"
  done
}

# scaffold <fixture> [with-profile]
#   with-profile also copies <fixture>.profile/ (a ready .claude/stackfoundry/ profile), for cases that test a
#   skill on an initialized repo rather than init itself.
scaffold() {
  name="$1"
  lib_dir=$(CDPATH= cd -- "$(dirname -- "$SCAFFOLD_LIB")" && pwd)
  src="$lib_dir/$name"
  [ -d "$src" ] || { echo "fixture not found: $src" >&2; exit 1; }
  copy_tree "$src"
  if [ "${2:-}" = "with-profile" ]; then
    [ -d "$src.profile" ] || { echo "profile not found: $src.profile" >&2; exit 1; }
    copy_tree "$src.profile"
  fi
  git init -q -b main
  git -c user.name=fixture -c user.email=fixture@example.invalid -c commit.gpgsign=false add -A
  git -c user.name=fixture -c user.email=fixture@example.invalid -c commit.gpgsign=false commit -q -m "fixture: $name"
}
