"""`stackfoundry globs-check` and `stackfoundry mutation-check`. Read-only.

globs-check <file|dir> ...
    For every rulebook (a Markdown file with a `paths:` frontmatter list), report each glob that matches no file in
    the repo. A rule whose globs match nothing never loads. Uses the same matcher as change-targets.

mutation-check <report.json>
    Reads a mutation report in the common "mutation-testing-elements" JSON schema (Stryker, Stryker.NET and other
    tools that emit it: files -> mutants -> status) and judges whether the run is evidence at all:
      - zero killed mutants means the tool is broken, not that the tests are weak;
      - more timeouts than kills means a starved runner (timeouts count as detected and inflate the score).
    Exit 1 when the report cannot be trusted.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from . import gitutil
from .frontmatter import split
from .globs import match


DETECTED = {"Killed", "Timeout"}
UNDETECTED = {"Survived", "NoCoverage"}
INVALID = {"CompileError", "RuntimeError", "Ignored", "Pending"}
UTC_NAMES = {"UTC", "ETC/UTC", "Z", "ZULU", "GMT", "ETC/GMT", "UNIVERSAL", "ETC/UNIVERSAL"}


def rulebooks(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        out += sorted(p.rglob("*.md")) if p.is_dir() else [p]
    return out


def repo_files(root: Path) -> list[str]:
    """Every tracked or untracked-but-not-ignored file. Unlike the survey, nothing is skipped: a rule may well
    govern a bin/ or build/ folder, and Claude Code loads it for any file there."""
    try:
        return gitutil.paths(["ls-files", "--cached", "--others", "--exclude-standard"], root)
    except gitutil.GitError:
        return [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]


def globs_check(root: Path, files: list[Path]) -> list[dict]:
    all_files = repo_files(root)
    results = []
    for f in rulebooks(files):
        fields, _, _ = split(f.read_text(encoding="utf-8", errors="replace"))
        globs = fields.get("paths")
        if not isinstance(globs, list):
            continue
        for g in globs:
            hits = sum(1 for rf in all_files if match(rf, str(g)))
            results.append({"file": f.as_posix(), "glob": g, "matches": hits})
    return results


def mutation_summary(report: dict) -> dict:
    counts: Counter = Counter()
    for entry in (report.get("files") or {}).values():
        for mutant in entry.get("mutants", []):
            counts[mutant.get("status", "Unknown")] += 1
    killed, timeout = counts["Killed"], counts["Timeout"]
    detected = killed + timeout
    valid = detected + sum(counts[s] for s in UNDETECTED)
    covered = detected + counts["Survived"]
    problems = []
    if killed == 0:
        problems.append("zero killed mutants: the tool or its test runner is broken; this is not evidence")
    if timeout > killed:
        problems.append(f"more timeouts ({timeout}) than kills ({killed}): a starved runner; rerun with fewer workers")
    if valid == 0:
        problems.append("no valid mutants (all compile errors, ignored or pending)")
    return {
        "counts": dict(counts),
        "scoreValid": round(100 * detected / valid, 1) if valid else None,
        "scoreCovered": round(100 * detected / covered, 1) if covered else None,
        "survivors": [
            {"file": name, "line": (m.get("location") or {}).get("start", {}).get("line"),
             "mutator": m.get("mutatorName"), "replacement": m.get("replacement")}
            for name, entry in (report.get("files") or {}).items()
            for m in entry.get("mutants", []) if m.get("status") == "Survived"
        ],
        "problems": problems,
    }


def main_globs(args) -> int:
    root = Path(args.root).resolve() if args.root else gitutil.repo_root(Path.cwd())
    results = globs_check(root, [p if p.is_absolute() else root / p for p in map(Path, args.paths)])
    dead = [r for r in results if r["matches"] == 0]
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in dead:
            print(f"{r['file']}: glob {r['glob']!r} matches no file")
        print(f"globs-check: {len(results)} glob(s), {len(dead)} matching nothing")
    return 1 if dead else 0


def today(root: Path) -> tuple[str, str]:
    """(YYYY-MM-DD, zone used) in targets.json's timezone. Python's zoneinfo needs a zone database (the OS's, or
    the tzdata package on Windows); without one the date is the machine's local date and the zone says so."""
    import datetime as dt

    zone = ""
    try:
        from .profile import TARGETS, load_json
        zone = load_json(root / TARGETS).get("timezone", "") if (root / TARGETS).exists() else ""
    except Exception:  # noqa: BLE001 - a broken profile still gets a date
        zone = ""
    if isinstance(zone, str) and zone.upper() in UTC_NAMES:
        # UTC needs no zone database, which Windows Python lacks unless the tzdata package is installed.
        return dt.datetime.now(dt.timezone.utc).date().isoformat(), zone
    if zone:
        try:
            from zoneinfo import ZoneInfo
            return dt.datetime.now(ZoneInfo(zone)).date().isoformat(), zone
        except Exception:  # noqa: BLE001 - no zone database
            return dt.date.today().isoformat(), f"local (no zone data for {zone}; pip install tzdata)"
    return dt.date.today().isoformat(), "local"


def main_today(args) -> int:
    root = Path(args.root).resolve() if args.root else Path.cwd()
    date, zone = today(root)
    print(date if not args.verbose else f"{date} ({zone})")
    return 0


def main_mutation(args) -> int:
    report = json.loads(Path(args.report).read_text(encoding="utf-8-sig"))
    s = mutation_summary(report)
    if args.json:
        print(json.dumps(s, indent=2))
    else:
        print(f"counts: {s['counts']}")
        print(f"score over valid mutants: {s['scoreValid']}%   over covered: {s['scoreCovered']}%")
        for sv in s["survivors"][:50]:
            print(f"survived: {sv['file']}:{sv['line']}  {sv['mutator']} -> {sv['replacement']}")
        for p in s["problems"]:
            print(f"problem: {p}")
    return 1 if s["problems"] else 0
