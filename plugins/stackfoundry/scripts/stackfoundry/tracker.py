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

A finding id is upper-case letters and digits in parts joined by `-`, optionally several joined by `/` (`B1`,
`SUMUP-1`, `A11Y-TARGET-SIZE`, `EL7/N26`), and holds at least one digit, so banner words (`OPEN`, `PARTIAL`) never
read as ids. In a banner, a token that is no finding id of the file reads as its `-`/`/` parts (`B1/B2` is two ids).

The banner lists open ids, never tallies: a count goes stale the moment one finding moves.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SEVERITIES = ("🔴", "🟡", "🔵")
OPEN_MARKERS = ("⬜", "⚠️", "⚠")
CLOSED_MARKERS = ("✅", "🚫")
_PART = r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*"
ID_TOKEN = rf"{_PART}(?:/{_PART})*"
FINDING = re.compile(rf"^#{{2,4}}\s+({ID_TOKEN})\s+(🔴|🟡|🔵)\s+(⬜|⚠️|⚠|✅|🚫)")
TD_ROW = re.compile(r"^\|\s*(TD-\d+)\s*\|(.*)\|\s*$")
TD_STATUS = ("⬜", "✍️", "✍", "✅", "⚠️", "⚠", "❓", "⏸️", "⏸", "🚫")
BANNER = re.compile(r"^\*\*Open:\*\*\s*(.*)$")
TALLY = re.compile(r"\b\d+\s+(?:open|fixed|closed|findings?|rows?|partial)\b", re.I)
ID = re.compile(rf"\b{ID_TOKEN}\b")
DIGIT = re.compile(r"\d")


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
        if (m := FINDING.match(line)) and DIGIT.search(m.group(1)):
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


def banner_ids(text: str, known: set[str]) -> list[str]:
    """The ids a banner segment names: a token that is a finding id of the file as is, any other split into its
    `-`/`/` parts, keeping only those with a digit (so `B1/B2` and `B1-B3` read as before ids could hold `-`)."""
    out: list[str] = []
    for token in ID.findall(text):
        if token in known:
            out.append(token)
        else:
            out += [p for p in re.split(r"[-/]", token) if DIGIT.search(p) and re.fullmatch(_PART, p)]
    return out


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
    known = set(ids)
    listed = set(banner_ids(open_part, known))
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
            if item["id"] in listed and (seg is None or item["id"] not in banner_ids(seg.group(1), known)):
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
