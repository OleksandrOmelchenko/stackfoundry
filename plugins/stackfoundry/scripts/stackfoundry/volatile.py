"""`stackfoundry volatile-facts <path>`: candidates for facts that are true for one commit only. Read-only.

Living text (skills, agents, rulebooks, specs, READMEs) should not carry them: `file:line`, dates, SHAs, measured
durations, and (with --include-counts) counts of code things. A hit is a candidate, not a verdict: a snapshot
document (a dated report) legitimately carries all of them. Fenced code blocks are skipped.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .globs import match_any

PATTERNS = {
    "file:line": re.compile(r"\b[\w./-]+\.(?:cs|ts|tsx|js|mjs|vue|py|go|rs|java|kt|rb|php|sql|md|json|ya?ml|ps1|sh|scss|css|html)"
                            r":\d+(?:-\d+)?\b"),
    "date": re.compile(r"\b(?:as of|since|updated|last checked)\s+\d{4}-\d{2}-\d{2}\b|\bas of (?:January|February|March|"
                       r"April|May|June|July|August|September|October|November|December|Q[1-4])\b", re.I),
    "sha": re.compile(r"(?<![\w/#-])(?=[0-9a-f]*[a-f])(?=[0-9a-f]*\d)[0-9a-f]{7,40}(?![\w-])"),
    "duration": re.compile(r"\b(?:takes|took|runs in|ran in|about|~)\s*\d+(?:\.\d+)?\s?(?:ms|s|sec|seconds|min|minutes|hours)\b",
                           re.I),
}
COUNT = re.compile(r"\b\d{2,}\s+(?:tests?|specs?|skills?|agents?|files?|projects?|endpoints?|controllers?|tables?|"
                   r"procs?|procedures?|rules?|findings?|packages?|components?|pages?|services?|lines?)\b", re.I)


def scan_text(text: str, include_counts: bool) -> list[dict]:
    hits = []
    in_fence = False
    for n, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        checks = dict(PATTERNS)
        if include_counts:
            checks["count"] = COUNT
        for kind, rx in checks.items():
            for m in rx.finditer(line):
                hits.append({"line": n, "kind": kind, "text": m.group(0)})
    return hits


def scan(path: Path, include_counts: bool, exclude: list[str]) -> list[dict]:
    files = [path] if path.is_file() else sorted(path.rglob("*.md"))
    out = []
    base = path if path.is_dir() else path.parent
    for f in files:
        rel = f.relative_to(base).as_posix()
        if match_any(rel, exclude):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for h in scan_text(text, include_counts):
            out.append({"file": f.as_posix(), **h})
    return out


def main(args) -> int:
    hits = scan(Path(args.path), args.include_counts, args.exclude or [])
    if args.json:
        print(json.dumps(hits, indent=2))
    else:
        for h in hits:
            print(f"{h['file']}:{h['line']}  [{h['kind']}]  {h['text']}")
        print(f"{len(hits)} candidate(s)")
    return 1 if (args.strict and hits) else 0
