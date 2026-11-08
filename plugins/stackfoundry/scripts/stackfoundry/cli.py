"""stackfoundry helper CLI. Run through bin/stackfoundry, which picks Python >= 3.10 and isolates it (-I).

Every subcommand is read-only except `manifest record` (writes .claude/stackfoundry/manifest.lock.json).
None makes a network call.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# -I leaves the script directory off sys.path; add this package's parent explicitly (our own code only).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stackfoundry import (backlog, change_targets, guard, manifest, plumbing, select_tests,  # noqa: E402
                          survey, tracker, volatile)
from stackfoundry.gitutil import GitError  # noqa: E402
from stackfoundry.profile import ProfileError  # noqa: E402


def build() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackfoundry", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True, metavar="<subcommand>")

    s = sub.add_parser("survey", help="read-only repo inventory as JSON (manifests, layers, tests, CI, generated code)")
    s.add_argument("path", nargs="?", default=".")
    s.add_argument("--pretty", action="store_true")
    s.set_defaults(func=survey.main)

    for name, mod, helptext in (
        ("change-targets", change_targets, "map a change set to targets and specialist reviewers"),
        ("select-tests", select_tests, "the test runs a change set needs, from targets.json"),
    ):
        c = sub.add_parser(name, help=helptext)
        c.add_argument("--base", help="compare base...HEAD (plus uncommitted); default: uncommitted + untracked")
        c.add_argument("--files", help="comma-separated paths instead of git")
        c.add_argument("--root", help="repo root (default: git toplevel of the current directory)")
        c.add_argument("--json", action="store_true")
        if name == "select-tests":
            c.add_argument("--mode", choices=["affected", "full"], default="affected")
        c.set_defaults(func=mod.main)

    v = sub.add_parser("volatile-facts", help="file:line, dates, SHAs, durations (and counts) in living docs")
    v.add_argument("path")
    v.add_argument("--include-counts", action="store_true")
    v.add_argument("--exclude", action="append", help="glob, relative to path (repeatable)")
    v.add_argument("--strict", action="store_true", help="exit 1 when anything is found")
    v.add_argument("--json", action="store_true")
    v.set_defaults(func=volatile.main)

    b = sub.add_parser("backlog", help="plans, spec follow-ups, open findings and test rows, TODOs")
    b.add_argument("--section", choices=["all", "plans", "bugs", "todos"], default="all")
    b.add_argument("--category")
    b.add_argument("--root")
    b.add_argument("--json", action="store_true")
    b.set_defaults(func=backlog.main)

    t = sub.add_parser("tracker", help="check or parse a bug report or test design")
    t.add_argument("action", choices=["check", "parse"])
    t.add_argument("file")
    t.set_defaults(func=tracker.main)

    vp = sub.add_parser("verify-plumbing", help="static checks of skill and agent definitions")
    vp.add_argument("dir", nargs="?", default=".")
    vp.add_argument("--json", action="store_true")
    vp.set_defaults(func=plumbing.main)

    m = sub.add_parser("manifest", help="record generated files, or diff them against their templates")
    m.add_argument("action", choices=["record", "diff", "list"])
    m.add_argument("files", nargs="*")
    m.add_argument("--template", help="plugin-relative template path, or 'research' for a researched pack")
    m.add_argument("--kind", choices=["generated", "materialized"], default="generated")
    m.add_argument("--root", default=".")
    m.add_argument("--json", action="store_true")
    m.set_defaults(func=manifest.main)

    g = sub.add_parser("guard", help="PreToolUse hook entry (reads the hook event on stdin)")
    g.set_defaults(func=guard.main)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # emoji markers on a Windows console
        except (AttributeError, ValueError):
            pass
    args = build().parse_args(argv)
    try:
        return args.func(args)
    except (ProfileError, GitError, FileNotFoundError) as exc:
        print(f"stackfoundry {args.command}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
