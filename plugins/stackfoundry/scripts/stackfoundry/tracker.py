"""Tracker parsing and `stackfoundry tracker check <file>`. Read-only.

Formats (reference/trackers/):

Bug report
    **Open:** 🔴 B1 · 🟡 B3, B4          (or **Open:** none)
    ### B1 🔴 ⬜ OPEN — short title
  Markers: ⬜ OPEN · ⚠️ PARTIAL (both open) · ✅ FIXED · 🚫 WONT-FIX. Severity: 🔴 · 🟡 · 🔵.

Test design
    **Open:** TD-1, TD-3 · **Questions:** Q1
    | TD-1 | behaviour | technique | layer | oracle | ⬜ |
  Status (last cell): ⬜ to write · ✍️ written · ✅ reviewed sound · ⚠️ flagged · ❓ question · ⏸ quarantined ·
  🚫 dropped. Open = anything but ✅ and 🚫.

The banner lists open ids, never tallies: a count goes stale the moment one finding moves.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SEVERITIES = ("🔴", "🟡", "🔵")
OPEN_MARKERS = ("⬜", "⚠️", "⚠")
CLOSED_MARKERS = ("✅", "🚫")
FINDING = re.compile(r"^#{2,4}\s+([A-Z]{1,3}\d+)\s+(🔴|🟡|🔵)\s+(⬜|⚠️|⚠|✅|🚫)")
TD_ROW = re.compile(r"^\|\s*(TD-\d+)\s*\|(.*)\|\s*$")
TD_STATUS = ("⬜", "✍️", "✍", "✅", "⚠️", "⚠", "❓", "⏸️", "⏸", "🚫")
BANNER = re.compile(r"^\*\*Open:\*\*\s*(.*)$")
TALLY = re.compile(r"\b\d+\s+(?:open|fixed|closed|findings?|rows?|partial)\b", re.I)
ID = re.compile(r"\b(?:TD-\d+|[A-Z]{1,3}\d+)\b")


def kind_of(text: str) -> str:
    if any(TD_ROW.match(line) for line in text.splitlines()):
        return "test-design"
    return "bug-report"


def parse_bug_report(text: str) -> dict:
    findings = []
    banner = None
    for n, line in enumerate(text.splitlines(), start=1):
        if banner is None and (b := BANNER.match(line)):
            banner = {"line": n, "text": b.group(1)}
        if m := FINDING.match(line):
            marker = m.group(3)
            findings.append({"id": m.group(1), "severity": m.group(2), "marker": marker, "line": n,
                             "open": marker in OPEN_MARKERS})
    return {"kind": "bug-report", "banner": banner, "items": findings}


def parse_test_design(text: str) -> dict:
    rows = []
    banner = None
    for n, line in enumerate(text.splitlines(), start=1):
        if banner is None and (b := BANNER.match(line)):
            banner = {"line": n, "text": b.group(1)}
        if m := TD_ROW.match(line):
            cells = [c.strip() for c in m.group(2).split("|")]
            last = cells[-1] if cells else ""
            status = next((s for s in TD_STATUS if last.startswith(s)), None)
            rows.append({"id": m.group(1), "status": status, "line": n,
                         "open": status not in ("✅", "🚫")})
    return {"kind": "test-design", "banner": banner, "items": rows}


def parse(text: str) -> dict:
    return parse_test_design(text) if kind_of(text) == "test-design" else parse_bug_report(text)


def is_tracker(text: str) -> bool:
    """A file with findings, test-design rows or an Open banner. Index READMEs, templates and ledgers such as
    deferred-upgrades.md are not trackers and have nothing to check."""
    doc = parse(text)
    return bool(doc["items"]) or doc["banner"] is not None


def check(text: str) -> list[str]:
    doc = parse(text)
    problems: list[str] = []
    items = doc["items"]
    if not items and doc["banner"] is None:
        return problems
    ids = [i["id"] for i in items]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        problems.append(f"duplicate ids: {', '.join(dupes)}")
    if doc["kind"] == "test-design":
        bad = [i["id"] for i in items if i["status"] is None]
        if bad:
            problems.append(f"rows without a status marker in the last cell: {', '.join(bad)}")
    open_ids = {i["id"] for i in items if i["open"]}
    banner = doc["banner"]
    if banner is None:
        problems.append("no '**Open:**' banner")
        return problems
    btext = banner["text"]
    if TALLY.search(btext):
        problems.append(f"line {banner['line']}: the banner carries a tally ({TALLY.search(btext).group(0)!r}); list open ids")
    open_part = btext.split("**Questions:**")[0]
    listed = set(ID.findall(open_part))
    if open_part.strip().lower().startswith("none"):
        listed = set()
    if listed - open_ids:
        problems.append(f"banner lists ids that are not open: {', '.join(sorted(listed - open_ids))}")
    if open_ids - listed:
        problems.append(f"open ids missing from the banner: {', '.join(sorted(open_ids - listed))}")
    if doc["kind"] == "bug-report":
        for item in items:
            if not item["open"]:
                continue
            seg = re.search(re.escape(item["severity"]) + r"([^🔴🟡🔵]*)", open_part)
            if item["id"] in listed and (seg is None or item["id"] not in ID.findall(seg.group(1))):
                problems.append(f"{item['id']} is listed under the wrong severity in the banner")
    return problems


def main(args) -> int:
    text = Path(args.file).read_text(encoding="utf-8")
    if args.action == "parse":
        print(json.dumps(parse(text), indent=2, ensure_ascii=False))
        return 0
    if not is_tracker(text):
        print(f"{args.file}: not a tracker (no findings, test-design rows or Open banner); nothing to check")
        return 0
    problems = check(text)
    for p in problems:
        print(f"{args.file}: {p}")
    if not problems:
        print(f"{args.file}: ok")
    return 1 if problems else 0
