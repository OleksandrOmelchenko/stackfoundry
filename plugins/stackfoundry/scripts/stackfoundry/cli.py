"""stackfoundry helper CLI. Run through scripts/stackfoundry.sh, which picks Python >= 3.11 and isolates it (-I).

Every subcommand is read-only except `manifest record|forget` (they write .stackfoundry/manifest.lock.json),
`pack render --out` and `render-rule|render-agent|render-rulebook --out|--write` (each writes the one file it names), and
`extensions new|base|merge|forget` (the extension file named, its base copy and .stackfoundry/extensions/.base/),
and `side-effects` (its state file, in the system temp folder).
None makes a network call.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# -I leaves the script directory off sys.path; add this package's parent explicitly (our own code only).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stackfoundry import (backlog, block, change_targets, checks, clients, config, extensions, guard,  # noqa: E402
                          manifest, pack, plumbing, product, rulebooks, select_tests, sideeffects, sizes, survey,
                          tracker, volatile)
from stackfoundry.gitutil import GitError  # noqa: E402
from stackfoundry.profile import ProfileError  # noqa: E402


class _Parser(argparse.ArgumentParser):
    """No abbreviated options (`--ro` for `--root`), in every subcommand: a typo must fail, not pick an option."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_abbrev", False)
        super().__init__(*args, **kwargs)


def build() -> argparse.ArgumentParser:
    p = _Parser(prog="stackfoundry", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True, metavar="<subcommand>", parser_class=_Parser)

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
        if name == "change-targets":
            c.add_argument("--all", action="store_true",
                           help="every tracked and untracked file: checks a whole profile (shadowed, unmapped)")
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
    gc.add_argument("paths", nargs="*", default=[".stackfoundry/rules"], help="rulebook files or folders (default .stackfoundry/rules)")
    gc.add_argument("--root")
    gc.add_argument("--json", action="store_true")
    gc.set_defaults(func=checks.main_globs)

    mc = sub.add_parser("mutation-check", help="(read-only) judge a mutation-testing-elements JSON report (zero kills = broken)")
    mc.add_argument("report")
    mc.add_argument("--json", action="store_true")
    mc.set_defaults(func=checks.main_mutation)

    sz = sub.add_parser("size-check", help="(read-only) sizes of the generated instruction files, rulebooks, skills and "
                                           "agents against each assistant's limits; exit 1 past a hard limit")
    sz.add_argument("--root")
    sz.add_argument("--json", action="store_true")
    sz.set_defaults(func=sizes.main)

    td = sub.add_parser("today", help="(read-only) today's date (YYYY-MM-DD) in targets.json's timezone, for report names")
    td.add_argument("--root")
    td.add_argument("--verbose", action="store_true", help="also print which zone was used")
    td.set_defaults(func=checks.main_today)

    cf = sub.add_parser("config", help="(read-only) the repo's settings from .stackfoundry/config.json, defaults filled in")
    cf.add_argument("key", nargs="?", help="one setting (clients, docsRoot, researchRefreshDays, defaultEffort)")
    cf.add_argument("--root", help="repo root (default: the nearest folder with .stackfoundry/, else the git root)")
    cf.add_argument("--json", action="store_true")
    cf.set_defaults(func=config.main)

    op = sub.add_parser("outputs", help="(read-only) where rulebooks, instruction blocks, skills and agents go for the repo's assistants")
    op.add_argument("--clients", help="comma-separated instead of config.json's clients")
    op.add_argument("--root")
    op.add_argument("--json", action="store_true")
    op.set_defaults(func=clients.main_outputs)

    for name, kind, src_help, choices in (
        ("render-rule", "rule", "a canonical rulebook (.stackfoundry/rules/<id>.md)", ["claude-code", "copilot", "cursor"]),
        ("render-agent", "agent", "a Claude Code agent file (.stackfoundry/agents/<name>.md)", list(clients.CLIENTS)),
    ):
        rr = sub.add_parser(name, help=f"convert {src_help} to an assistant's format: stdout, or writes --out | --write")
        rr.add_argument("source")
        rr.add_argument("--client", required=True, choices=choices)
        dest = rr.add_mutually_exclusive_group()
        dest.add_argument("--out", help="write here")
        dest.add_argument("--write", action="store_true", help="write to the assistant's standard location")
        rr.add_argument("--root", help="repo root for --write (default: the nearest folder with .stackfoundry/)")
        rr.set_defaults(func=lambda a, k=kind: clients.main_render(a, k))

    rb = sub.add_parser("render-rulebook", help="fill a shared rulebook (testing, dependency-bumps, documentation, "
                                                "benchmarking) from the profile: stdout, or writes --out | --write")
    rb.add_argument("name", choices=list(rulebooks.NAMES))
    rbd = rb.add_mutually_exclusive_group()
    rbd.add_argument("--out", help="write here")
    rbd.add_argument("--write", action="store_true", help="write the canonical .stackfoundry/rules/<name>.md")
    rb.add_argument("--root", help="repo root (default: the nearest folder with .stackfoundry/)")
    rb.set_defaults(func=rulebooks.main)

    bl = sub.add_parser("render-block", help="the stackfoundry block of an instruction file (CLAUDE.md, AGENTS.md, "
                                             "GEMINI.md) from the profile: stdout, or writes --out | --write")
    bl.add_argument("file", nargs="?", help="one instruction file (default with --write: every one the assistants read)")
    bld = bl.add_mutually_exclusive_group()
    bld.add_argument("--out", help="write the block alone here")
    bld.add_argument("--write", action="store_true", help="splice the block between the file's markers, or append it")
    bl.add_argument("--root", help="repo root (default: the nearest folder with .stackfoundry/)")
    bl.set_defaults(func=block.main)

    pk = sub.add_parser("pack", help="check a researched pack (read-only), or render its rulebook (writes only --out)")
    pk.add_argument("action", choices=["check", "render"])
    pk.add_argument("pack", help="path to .stackfoundry/packs/<id>/pack.json")
    pk.add_argument("--out", help="render: write the rulebook here instead of stdout")
    pk.add_argument("--json", action="store_true")
    pk.set_defaults(func=pack.main)

    pr = sub.add_parser("product", help="(read-only) check the product profile or a domain brief, or show their status")
    pr.add_argument("action", choices=["check", "status"])
    pr.add_argument("file", nargs="?", help="check: .stackfoundry/product.json or .stackfoundry/domain/<id>.json")
    pr.add_argument("--root", help="status: repo root (default: the nearest folder with .stackfoundry/)")
    pr.set_defaults(func=product.main)

    m = sub.add_parser("manifest", help="record|forget write manifest.lock.json; diff|list are read-only")
    m.add_argument("action", choices=["record", "forget", "diff", "list"])
    m.add_argument("files", nargs="*")
    m.add_argument("--template", help="plugin-relative template path; 'research' for a pack and its rulebook; "
                                      "'profile' for profile facts (targets.json, ecosystems.json, guards.json…)")
    m.add_argument("--kind", choices=["generated", "materialized"], default="generated")
    m.add_argument("--root", default=".")
    m.add_argument("--json", action="store_true")
    m.set_defaults(func=manifest.main)

    ex = sub.add_parser("extensions", help="repo changes to plugin skills and agents: list|check are read-only; "
                                           "new|base|merge|forget write under .stackfoundry/")
    ex.add_argument("action", choices=["list", "check", "new", "base", "merge", "forget"])
    ex.add_argument("names", nargs="*", help="new: skill|agent <name>; base|merge|forget: the file")
    ex.add_argument("--replace", action="store_true", help="new: a full copy instead of anchored additions")
    ex.add_argument("--from", dest="source", help="base: the plugin file it was copied from (agents/<role>.md)")
    ex.add_argument("--resolved", action="store_true", help="merge: take the settled <file>.merge.md")
    ex.add_argument("--plugin-root", help="the plugin to compare with (default: this one)")
    ex.add_argument("--root", help="repo root (default: the nearest folder with .stackfoundry/)")
    ex.add_argument("--json", action="store_true")
    ex.set_defaults(func=extensions.main)

    g = sub.add_parser("guard", help="(read-only) pre-tool hook entry for every assistant: reads the hook event on stdin")
    g.add_argument("--client", choices=["auto", "antigravity", "claude-code", "codex", "copilot", "cursor", "gemini"], default="auto",
                   help="the assistant sending the event (default: told by the event's shape)")
    g.add_argument("--check", action="store_true", help="validate guards.json instead of reading a hook event")
    g.add_argument("--root", help="repo root for --check (default: CLAUDE_PROJECT_DIR or the current directory)")
    g.set_defaults(func=guard.main)

    se = sub.add_parser("side-effects", help="start|end: prove an unattended run changed nothing but its report "
                                             "(writes only its state file in the system temp folder)")
    se.add_argument("action", choices=["start", "end"])
    se.add_argument("--allow", action="append", metavar="GLOB", help="end: a path the run may change (its report)")
    se.add_argument("--root", help="repo root (default: the nearest folder with .stackfoundry/)")
    se.add_argument("--json", action="store_true")
    se.set_defaults(func=sideeffects.main)
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
    except (ProfileError, GitError, OSError, ValueError, RecursionError) as exc:
        # 2 = could not run (missing or malformed input). 1 means "ran and found something"; a crash must never
        # read as a verdict. ValueError covers JSON and Unicode decode errors; RecursionError, absurdly nested JSON.
        print(f"stackfoundry {args.command}: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - a bug in a command must not read as "found something" (exit 1)
        print(f"stackfoundry {args.command}: internal error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 0 if args.command == "guard" else 2


if __name__ == "__main__":
    sys.exit(main())
