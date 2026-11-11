"""`stackfoundry size-check`: the size of everything stackfoundry generated into a repo, against what each of the repo's
assistants reads. Read-only.

It measures, for the assistants in config.json `clients`:
  - each instruction file (CLAUDE.md, AGENTS.md, GEMINI.md): the whole file, which the host loads, and the
    stackfoundry block inside it, which is this plugin's share;
  - every canonical rulebook (.stackfoundry/rules/) and each assistant's copy of it;
  - the repo's skills in each skills folder `stackfoundry outputs` lists, and the materialized agents.
Lines and bytes are exact; tokens are estimated as bytes/4. The limits come from `clients.LIMITS` (sources in
reference/clients.md): past a hard limit (where the host stops reading) is an error, exit 1; past a soft one (the
host's advice) is a warning. Every measured file is listed, so the cost is visible before anything breaks. A rulebook
over a limit is tightened by refreshing its pack (`research-stack`), never by truncating the render.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config
from .block import BLOCK, instruction_files
from .clients import LIMITS, RULE_FORMATS, outputs
from .profile import find_root

RULES = Path(".stackfoundry") / "rules"
AGENTS = Path(".stackfoundry") / "agents"


def measure(text: str) -> dict:
    data = text.encode("utf-8")
    return {"lines": len(text.splitlines()), "bytes": len(data), "tokens": (len(data) + 3) // 4}


def _limits(kind: str, clients: list[str]) -> list[tuple[str, str, int, bool]]:
    table = LIMITS.get(kind, {})
    out = [(c, *lim) for c in clients for lim in table.get(c, [])]
    out += [("every assistant", *lim) for lim in table.get("*", [])]
    return out


def _judge(row: dict, limits: list[tuple[str, str, int, bool]]) -> None:
    for client, unit, value, hard in limits:
        if row[unit] > value:
            what = f"{row[unit]} {unit} > {value} ({client}{', hard limit' if hard else ' advice'})"
            (row["errors"] if hard else row["warnings"]).append(what)


def check(root: Path) -> list[dict]:
    clients = config.load(root)["clients"]
    rows: list[dict] = []

    def add(path: Path, kind: str, limits, text: str | None = None, **extra) -> None:
        text = path.read_text(encoding="utf-8-sig") if text is None else text
        row = {"path": path.relative_to(root).as_posix(), "kind": kind, **measure(text), **extra,
               "errors": [], "warnings": []}
        _judge(row, limits)
        rows.append(row)

    for rel, readers in instruction_files(root, clients).items():
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        found = BLOCK.search(text)
        add(path, "instructions", _limits("instructions", readers), text,
            block_lines=len(found.group(0).splitlines()) if found else 0)

    canonical = sorted((root / RULES).glob("*.md")) if (root / RULES).is_dir() else []
    for f in canonical:
        add(f, "rulebook", [])
        for client in clients:
            if client not in RULE_FORMATS:
                continue
            folder, suffix = RULE_FORMATS[client]
            copy = root / folder / f"{f.stem}{suffix}"
            if copy.is_file():
                add(copy, "rule", _limits("rule", [client]))

    seen = set()
    for folder in outputs(clients)["skills"]:
        for f in sorted((root / folder).glob("*/SKILL.md")) if (root / folder).is_dir() else []:
            if f.resolve() not in seen:
                seen.add(f.resolve())
                add(f, "skill", _limits("skill", clients))
    for f in sorted((root / AGENTS).glob("*.md")) if (root / AGENTS).is_dir() else []:
        add(f, "agent", [])
    return rows


def main(args) -> int:
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    rows = check(root)
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            block = f", block {r['block_lines']} lines" if "block_lines" in r else ""
            print(f"{r['path']}: {r['lines']} lines, {r['bytes']} bytes, ~{r['tokens']} tokens{block}")
            for e in r["errors"]:
                print(f"  error: {e}")
            for w in r["warnings"]:
                print(f"  warning: {w}")
        errors = sum(len(r["errors"]) for r in rows)
        warnings = sum(len(r["warnings"]) for r in rows)
        print(f"size-check: {len(rows)} file(s), {errors} error(s), {warnings} warning(s)")
    return 1 if any(r["errors"] for r in rows) else 0
