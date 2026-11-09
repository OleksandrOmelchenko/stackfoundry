"""stackfoundry helper CLI. Run through scripts/stackfoundry.sh, which picks Python >= 3.11 and isolates it (-I).

Every subcommand is read-only except `manifest record|forget` (they write .stackfoundry/manifest.lock.json)
and `pack render --out` (writes the rulebook it names).
None makes a network call.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# -I leaves the script directory off sys.path; add this package's parent explicitly (our own code only).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stackfoundry import (backlog, change_targets, checks, config, guard, manifest, pack,  # noqa: E402
                          plumbing, select_tests, survey, tracker, volatile)
from stackfoundry.gitutil import GitError  # noqa: E402
from stackfoundry.profile import ProfileError  # noqa: E402


def build() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stackfoundry", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True, metavar="<subcommand>")

    s = sub.add_parser("survey", help="(read-only) repo inventory as JSON: manifests, layers, tests, CI, generated code")
    s.add_argument("path", nargs="?", default=".")
    s.add_argument("--pretty", action="store_true")
    s.set_defaults(func=survey.main)

    for name, mod, helptext in (
        ("change-targets", change_targets, "(read-only) map a change set to targets and specialist reviewers"),
        ("select-tests", select_tests, "(read-only) the test runs a change set needs, from targets.json; runs nothing"),
    ):
        c = sub.add_parser(name, help=helptext)
        c.add_argument("--base", help="compare base...HEAD (plus uncommitted); default: uncommitted + untracked")
        c.add_argument("--files", nargs="+", help="paths instead of git (space- or comma-separated)")
        c.add_argument("--range", help="a commit range (A..B or A...B) exactly, without uncommitted changes")
        c.add_argument("--root", help="repo root (default: git toplevel of the current directory)")
        c.add_argument("--json", action="store_true")
        if name == "select-tests":
            c.add_argument("--mode", choices=["affected", "full"], default="affected")
        c.set_defaults(func=mod.main)

    v = sub.add_parser("volatile-facts", help="(read-only) file:line, dates, SHAs, durations (and counts) in living docs")
    v.add_argument("paths", nargs="+", help="files or folders")
    v.add_argument("--include-counts", action="store_true")
    v.add_argument("--exclude", action="append", help="glob, relative to path (repeatable)")
    v.add_argument("--strict", action="store_true", help="exit 1 when anything is found")
    v.add_argument("--json", action="store_true")
    v.set_defaults(func=volatile.main)

    b = sub.add_parser("backlog", help="(read-only) plans, spec follow-ups, open findings and test rows, TODOs")
    b.add_argument("--section", choices=["all", "plans", "bugs", "todos"], default="all")
    b.add_argument("--category")
    b.add_argument("--root")
    b.add_argument("--json", action="store_true")
    b.set_defaults(func=backlog.main)

    t = sub.add_parser("tracker", help="(read-only) check or parse a bug report or test design")
    t.add_argument("action", choices=["check", "parse"])
    t.add_argument("file")
    t.set_defaults(func=tracker.main)

    vp = sub.add_parser("verify-plumbing", help="(read-only) static checks of skill and agent definitions")
    vp.add_argument("dir", nargs="?", default=".")
    vp.add_argument("--json", action="store_true")
    vp.set_defaults(func=plumbing.main)

    gc = sub.add_parser("globs-check", help="(read-only) rulebook paths: globs that match no file in the repo")
    gc.add_argument("paths", nargs="*", default=[".claude/rules"], help="rulebook files or folders (default .claude/rules)")
    gc.add_argument("--root")
    gc.add_argument("--json", action="store_true")
    gc.set_defaults(func=checks.main_globs)

    mc = sub.add_parser("mutation-check", help="(read-only) judge a mutation-testing-elements JSON report (zero kills = broken)")
    mc.add_argument("report")
    mc.add_argument("--json", action="store_true")
    mc.set_defaults(func=checks.main_mutation)

    td = sub.add_parser("today", help="(read-only) today's date (YYYY-MM-DD) in targets.json's timezone, for report names")
    td.add_argument("--root")
    td.add_argument("--verbose", action="store_true", help="also print which zone was used")
    td.set_defaults(func=checks.main_today)

    cf = sub.add_parser("config", help="(read-only) the repo's settings from .stackfoundry/config.json, defaults filled in")
    cf.add_argument("key", nargs="?", help="one setting (clients, docsRoot, researchRefreshDays, defaultEffort)")
    cf.add_argument("--root", help="repo root (default: the nearest folder with .stackfoundry/, else the git root)")
    cf.add_argument("--json", action="store_true")
    cf.set_defaults(func=config.main)

    pk = sub.add_parser("pack", help="check a researched pack (read-only), or render its rulebook (writes only --out)")
    pk.add_argument("action", choices=["check", "render"])
    pk.add_argument("pack", help="path to .stackfoundry/packs/<id>/pack.json")
    pk.add_argument("--out", help="render: write the rulebook here instead of stdout")
    pk.add_argument("--json", action="store_true")
    pk.set_defaults(func=pack.main)

    m = sub.add_parser("manifest", help="record|forget write manifest.lock.json; diff|list are read-only")
    m.add_argument("action", choices=["record", "forget", "diff", "list"])
    m.add_argument("files", nargs="*")
    m.add_argument("--template", help="plugin-relative template path; 'research' for a pack and its rulebook; "
                                      "'profile' for profile facts (targets.json, ecosystems.json, guards.json…)")
    m.add_argument("--kind", choices=["generated", "materialized"], default="generated")
    m.add_argument("--root", default=".")
    m.add_argument("--json", action="store_true")
    m.set_defaults(func=manifest.main)

    g = sub.add_parser("guard", help="(read-only) PreToolUse hook entry: reads the hook event on stdin")
    g.add_argument("--check", action="store_true", help="validate guards.json instead of reading a hook event")
    g.add_argument("--root", help="repo root for --check (default: CLAUDE_PROJECT_DIR or the current directory)")
    g.set_defaults(func=guard.main)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")  # emoji markers on a Windows console
        except (AttributeError, ValueError):
            pass
    argv = sys.argv[1:] if argv is None else argv
    try:
        args = build().parse_args(argv)
    except SystemExit as exc:
        # As a PreToolUse hook, exit 2 would block every tool call. A guard that cannot parse its command line
        # has no opinion instead.
        if argv[:1] == ["guard"] and exc.code not in (0, None):
            return 0
        raise
    try:
        return args.func(args)
    except (ProfileError, GitError, OSError, ValueError) as exc:
        # 2 = could not run (missing or malformed input). 1 means "ran and found something"; a crash must never
        # read as a verdict. ValueError covers JSON and Unicode decode errors.
        print(f"stackfoundry {args.command}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
