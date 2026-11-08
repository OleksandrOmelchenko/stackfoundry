"""`stackfoundry backlog`: everything pending, from the trackers. Read-only.

Sections: plans (docs/plans), spec follow-ups (docs/specifications, `## Follow-ups`), open bug-report findings,
open test-design rows, and TODO/FIXME comments in tracked code. A plan or spec without a valid line-3
`**Category:**` is a lint finding and makes the exit code 1.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import gitutil
from .profile import TARGETS, load_json
from .tracker import FINDING, parse_bug_report, parse_test_design

CATEGORY = re.compile(r"^\*\*Category:\*\*\s*([a-z0-9-]+)\s*$")
# POSIX ERE, no \b: `git grep -E` uses the system regex library, and macOS's has no word boundaries.
TODO = r"(^|[^A-Za-z0-9_])(TODO|FIXME)[:(]"


def docs_root(root: Path) -> Path:
    path = root / TARGETS
    if path.exists():
        try:
            return root / load_json(path).get("docsRoot", "docs")
        except Exception:  # noqa: BLE001 - a broken profile still lets the backlog run with the default
            pass
    return root / "docs"


def _docs(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob("*.md") if p.name != "README.md" and not p.name.startswith("_"))


def _title(lines: list[str], fallback: str) -> str:
    return next((line[2:].strip() for line in lines if line.startswith("# ")), fallback)


def plans(docs: Path, root: Path, lint: list[str]) -> list[dict]:
    out = []
    for p in _docs(docs / "plans"):
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        cat = CATEGORY.match(lines[2]) if len(lines) > 2 else None
        if not cat:
            lint.append(f"{p.relative_to(root).as_posix()}: line 3 is not a '**Category:** <word>' line")
        out.append({"file": p.relative_to(root).as_posix(), "title": _title(lines, p.stem),
                    "category": cat.group(1) if cat else None})
    return out


def follow_ups(docs: Path, root: Path, lint: list[str]) -> list[dict]:
    out = []
    for p in _docs(docs / "specifications"):
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        cat = CATEGORY.match(lines[2]) if len(lines) > 2 else None
        if not cat:
            lint.append(f"{p.relative_to(root).as_posix()}: line 3 is not a '**Category:** <word>' line")
        inside = False
        for n, line in enumerate(lines, start=1):
            if line.startswith("## "):
                inside = line[3:].strip().lower().startswith("follow-up")
                continue
            if inside and re.match(r"^\s*[-*]\s+\S", line) and not re.match(r"^\s*[-*]\s+(none|n/a)\.?\s*$", line, re.I):
                out.append({"file": p.relative_to(root).as_posix(), "line": n, "category": cat.group(1) if cat else None,
                            "text": line.strip()[2:].strip()})
    return out


def bugs(docs: Path, root: Path) -> list[dict]:
    """Open findings of bug reports and open gaps of threat models (same finding format)."""
    out = []
    for p in _docs(docs / "bug-reports") + _docs(docs / "security"):
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for item in parse_bug_report(text)["items"]:
            if item["open"]:
                heading = FINDING.sub("", lines[item["line"] - 1]).strip(" —-")
                out.append({"file": p.relative_to(root).as_posix(), "line": item["line"], "id": item["id"],
                            "severity": item["severity"], "marker": item["marker"], "title": heading})
    return out


def test_rows(docs: Path, root: Path) -> list[dict]:
    out = []
    for p in _docs(docs / "test-designs"):
        for row in parse_test_design(p.read_text(encoding="utf-8", errors="replace"))["items"]:
            if row["open"]:
                out.append({"file": p.relative_to(root).as_posix(), "line": row["line"], "id": row["id"],
                            "status": row["status"]})
    return out


def todos(root: Path, docs: Path) -> list[dict]:
    try:
        out = gitutil.run(["grep", "-n", "-I", "-E", "-i", TODO, "--", ".", f":(exclude){docs.relative_to(root).as_posix()}"],
                          root)
    except gitutil.GitError:
        return []  # git grep exits 1 when nothing matches
    items = []
    for line in out.splitlines()[:500]:
        parts = line.split(":", 2)
        if len(parts) == 3:
            items.append({"file": parts[0], "line": int(parts[1]), "text": parts[2].strip()[:160]})
    return items


def collect(root: Path, sections: set[str]) -> dict:
    docs = docs_root(root)
    lint: list[str] = []
    result: dict = {"docsRoot": docs.relative_to(root).as_posix()}
    if "plans" in sections:
        result["plans"] = plans(docs, root, lint)
        result["followUps"] = follow_ups(docs, root, lint)
    if "bugs" in sections:
        result["bugs"] = bugs(docs, root)
        result["testDesigns"] = test_rows(docs, root)
    if "todos" in sections:
        result["todos"] = todos(root, docs)
    result["lint"] = lint
    return result


def render(r: dict, category: str | None) -> str:
    out = []
    if "plans" in r:
        plans_ = [p for p in r["plans"] if not category or p["category"] == category]
        out.append(f"## Plans ({len(plans_)})")
        out += [f"- [{p['category'] or '?'}] {p['title']} ({p['file']})" for p in plans_]
        fus = [f for f in r["followUps"] if not category or f["category"] == category]
        out += ["", f"## Spec follow-ups ({len(fus)})"]
        out += [f"- [{f['category'] or '?'}] {f['text']} ({f['file']}:{f['line']})" for f in fus]
    if "bugs" in r:
        out += ["", f"## Open findings ({len(r['bugs'])})"]
        out += [f"- {b['severity']} {b['marker']} {b['id']} {b['title']} ({b['file']}:{b['line']})" for b in r["bugs"]]
        out += ["", f"## Open test-design rows ({len(r['testDesigns'])})"]
        out += [f"- {t['status'] or '?'} {t['id']} ({t['file']}:{t['line']})" for t in r["testDesigns"]]
    if "todos" in r:
        out += ["", f"## TODO / FIXME ({len(r['todos'])})"]
        out += [f"- {t['file']}:{t['line']}  {t['text']}" for t in r["todos"]]
    if r["lint"]:
        out += ["", "## Lint"] + [f"- {x}" for x in r["lint"]]
    return "\n".join(out).lstrip() + "\n"


def main(args) -> int:
    root = Path(args.root).resolve() if args.root else gitutil.repo_root(Path.cwd())
    sections = {"plans", "bugs", "todos"} if args.section == "all" else {args.section}
    r = collect(root, sections)
    print(json.dumps(r, indent=2, ensure_ascii=False) if args.json else render(r, args.category), end="")
    return 1 if r["lint"] else 0
