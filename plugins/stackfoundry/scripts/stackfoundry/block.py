"""`stackfoundry render-block [file] [--write | --out <path>]`: the stackfoundry block of an instruction file.

The block (reference/templates/instructions-block.md) sits between the stackfoundry markers in each instruction file
`stackfoundry outputs` lists. It is generated from the profile, never written by hand, and kept short: an
instruction file is loaded into every session.
  - Where every assistant reading the file loads path-scoped rules by itself (Claude Code, Copilot, Cursor,
    Antigravity), one paragraph says so and where each target's stack is listed. A table there would repeat what
    the host already does, at a cost on every turn (Claude Code's memory docs: keep CLAUDE.md short, move
    part-of-the-codebase instructions into path-scoped rules).
  - Where any reader has no path scoping (Codex, Gemini), the table is how it learns which rulebook applies: one
    loading sentence per reader, then one row per canonical rulebook in .stackfoundry/rules/ with a link relative to
    the file, its globs, and what it covers (frontmatter `covers`, else the head of its `description`).
  - The target names from targets.json.
`--write` splices the block between the file's markers, or appends it, keeping everything outside them and the
file's own line endings. Without a file name, `--write` writes every instruction file the repo's assistants read.
"""
from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

from . import REFERENCE, config
from .clients import CLIENTS, INSTRUCTION_FILES, RULE_FORMATS, _write
from .frontmatter import split
from .profile import ProfileError, find_root, load_targets
from .rulebooks import NAMES as SHARED

TEMPLATE = REFERENCE / "templates" / "instructions-block.md"
RULES = Path(".stackfoundry") / "rules"
BLOCK = re.compile(r"<!-- stackfoundry:begin.*?<!-- stackfoundry:end -->", re.S)
NAMES = {"claude-code": "Claude Code", "copilot": "Copilot", "cursor": "Cursor", "antigravity": "Antigravity CLI"}
READ_FIRST = "Before editing a file that matches a rulebook's globs, read that rulebook."


def instruction_files(root: Path, clients: list[str]) -> dict[str, list[str]]:
    """Each instruction file the repo's assistants read (relative path) -> the assistants that read it. CLAUDE.md is the
    root one when it exists, else `.claude/CLAUDE.md` when that exists, else a new root one (init's rule)."""
    out: dict[str, list[str]] = {}
    for c in CLIENTS:
        if c not in clients:
            continue
        name = INSTRUCTION_FILES[c]
        if name == "CLAUDE.md" and not (root / name).is_file() and (root / ".claude" / name).is_file():
            name = ".claude/CLAUDE.md"
        out.setdefault(name, []).append(c)
    return out


def _scoped(readers: list[str]) -> str:
    """The paragraph for a file whose every reader loads path-scoped rules by itself."""
    where = ", ".join(f"{NAMES[c]} from `{RULE_FORMATS[c][0]}/`" for c in readers)
    return textwrap.fill(f"The rulebooks in `{RULES.as_posix()}/` load by themselves when a matching file is read or "
                         f"written ({where}). Each target's stack is in `.stackfoundry/targets/<target>.md`.",
                         width=117, break_long_words=False, break_on_hyphens=False)


def _sentences(readers: list[str]) -> str:
    lines = [f"{NAMES[c]} loads each rulebook's copy in `{RULE_FORMATS[c][0]}/` when it reads a matching file."
             for c in readers if c in RULE_FORMATS]
    if any(c not in RULE_FORMATS for c in readers):
        lines.append(READ_FIRST)
    return " ".join(lines)


def _covers(fields: dict) -> str:
    covers = str(fields.get("covers") or "").strip()
    if covers:
        return covers
    desc = " ".join(str(fields.get("description") or "").split())
    if " rulebook (" in desc:  # a pack rulebook: "<title> rulebook (<layer> layer). Researched …"
        return desc.split(" rulebook (")[0]
    first = re.split(r"(?<=[.;])\s|\s—\s", desc, maxsplit=1)[0].rstrip(".;")
    return first


def _order(root: Path, targets: dict) -> list[str]:
    present = sorted(p.stem for p in (root / RULES).glob("*.md")) if (root / RULES).is_dir() else []
    order = [p for t in targets.get("targets", []) for p in t.get("packs", []) or []]
    order += list(SHARED)
    ranked = list(dict.fromkeys(i for i in order if i in present))
    return ranked + [i for i in present if i not in ranked]


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def rows(root: Path, file_rel: str, targets: dict) -> list[str]:
    depth = len(Path(file_rel).parent.parts)
    prefix = "../" * depth + RULES.as_posix()
    out = []
    for rid in _order(root, targets):
        fields, _, errors = split((root / RULES / f"{rid}.md").read_text(encoding="utf-8-sig"))
        if errors:
            raise ValueError(f"{RULES.as_posix()}/{rid}.md: {'; '.join(errors)}")
        paths = fields.get("paths") or []
        if isinstance(paths, str):
            paths = [paths]
        applies = ", ".join(f"`{_cell(str(p))}`" for p in paths) or "(no paths: loads nowhere)"
        out.append(f"| [{rid}]({prefix}/{rid}.md) | {applies} | {_cell(_covers(fields))} |")
    return out


def render(root: Path, file_rel: str, readers: list[str]) -> str:
    template = TEMPLATE.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    _, body, errors = split(template)
    if errors:
        raise ValueError(f"{TEMPLATE.name}: {'; '.join(errors)}")
    targets = load_targets(root)
    if all(c in RULE_FORMATS for c in readers):
        rulebooks = _scoped(readers)
    else:
        table = rows(root, file_rel, targets)
        if not table:
            raise ProfileError("no rulebooks in .stackfoundry/rules/: write them before the block")
        rulebooks = "\n".join([_sentences(readers), "", "| Rulebook | Applies to | Covers |", "|---|---|---|", *table])
    names = ", ".join(f"`{t['name']}`" for t in targets.get("targets", [])) or "none"
    text = (body.strip("\n").replace("{{rulebooks}}", rulebooks).replace("{{target names}}", names))
    left = sorted(set(re.findall(r"\{\{[^}]*\}\}", text)))
    if left:
        raise ValueError(f"instructions block: unfilled placeholders {left}")
    return text + "\n"


def splice(existing: str | None, block: str) -> str:
    """The file with its block replaced, or the block appended after a blank line; text outside the markers kept."""
    if not existing:
        return block
    block = block.rstrip("\n")
    if BLOCK.search(existing):
        return BLOCK.sub(lambda _: block, existing, count=1)
    return existing.rstrip("\n") + "\n\n" + block + "\n"


def write(root: Path, file_rel: str, readers: list[str]) -> None:
    path = root / file_rel
    raw = path.read_bytes() if path.is_file() else b""
    crlf = raw.count(b"\r\n") > raw.count(b"\n") // 2 if raw else False
    existing = raw.decode("utf-8-sig").replace("\r\n", "\n") if raw else None
    _write(root, file_rel, splice(existing, render(root, file_rel, readers)), newline="\r\n" if crlf else "\n")


def main(args) -> int:
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    files = instruction_files(root, config.load(root)["clients"])
    if args.file:
        given = Path(args.file)
        rel = (given.resolve().relative_to(root) if given.is_absolute() else given).as_posix().removeprefix("./")
        if rel not in files:
            print(f"render-block: {rel} is not an instruction file of this repo's assistants "
                  f"({', '.join(files) or 'none'})", file=sys.stderr)
            return 2
        files = {rel: files[rel]}
    if args.write:
        for rel, readers in files.items():
            write(root, rel, readers)
        return 0
    if len(files) != 1:
        print(f"render-block: name one instruction file ({', '.join(files)}) or pass --write", file=sys.stderr)
        return 2
    (rel, readers), = files.items()
    text = render(root, rel, readers)
    if args.out:
        _write(Path.cwd(), args.out, text)
    else:
        try:
            sys.stdout.reconfigure(newline="\n")  # LF even when redirected to a file on Windows
        except (AttributeError, ValueError):
            pass
        sys.stdout.write(text)
    return 0
