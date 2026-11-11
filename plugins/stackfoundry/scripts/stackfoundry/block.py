"""`stackfoundry render-block [file] [--write | --out <path>]`: the stackfoundry block of an instruction file.

The block (reference/templates/instructions-block.md) sits between the stackfoundry markers in each instruction file
`stackfoundry outputs` lists. It is generated from the profile, never written by hand, and kept short: an
instruction file is loaded into every session.
  - An assistant loads the rulebooks by itself only when it has path-scoped rules (Claude Code, Copilot, Cursor,
    Antigravity) AND its rules folder holds a copy of every canonical rulebook; a repo may keep them only in
    .stackfoundry/rules/. Where every reader of the file does, one paragraph says so and where each target's stack
    is listed: a table would repeat what the host already does, at a cost on every turn (Claude Code's memory
    docs: keep CLAUDE.md short, move part-of-the-codebase instructions into path-scoped rules).
  - Every other reader (Codex, Gemini, or a host without the copies) is told to read a rulebook before editing a
    matching file, with the table: one row per canonical rulebook in .stackfoundry/rules/, with a link relative to
    the file, its globs, and what it covers (frontmatter `covers`, else the head of its `description`). A table
    past BLOCK_BUDGET goes to .stackfoundry/rulebooks.md instead, which the block links.
  - The target names from targets.json.
`--write` splices the block between the file's markers, or appends it, keeping everything outside them and the
file's own line endings. Without a file name, `--write` writes every instruction file the repo's assistants read.
"""
from __future__ import annotations

import posixpath
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
INDEX = Path(".stackfoundry") / "rulebooks.md"  # outside rules/, where every *.md is a rulebook
# stackfoundry's own budget for the rulebook table inside an always-loaded instruction file, like plumbing.LISTING_CAP:
# about 2,000 tokens. A larger table (a repo with dozens of packs ran to 40 KB, past Codex's 32 KiB) goes to INDEX.
BLOCK_BUDGET = 8 * 1024


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


def _ids(root: Path) -> list[str]:
    return sorted(p.stem for p in (root / RULES).glob("*.md")) if (root / RULES).is_dir() else []


def _loads_itself(root: Path, client: str, ids: list[str]) -> bool:
    """The assistant has path-scoped rules and its folder holds a copy of every canonical rulebook."""
    if client not in RULE_FORMATS:
        return False
    folder, suffix = RULE_FORMATS[client]
    return all((root / folder / f"{rid}{suffix}").is_file() for rid in ids)


def _scoped(readers: list[str]) -> str:
    """The paragraph for a file whose every reader loads path-scoped rules by itself."""
    where = ", ".join(f"{NAMES[c]} from `{RULE_FORMATS[c][0]}/`" for c in readers)
    return textwrap.fill(f"The rulebooks in `{RULES.as_posix()}/` load by themselves when a matching file is read or "
                         f"written ({where}). Each target's stack is in `.stackfoundry/targets/<target>.md`.",
                         width=117, break_long_words=False, break_on_hyphens=False)


def _sentences(loading: list[str]) -> str:
    """One sentence per reader that loads the rulebooks by itself; the rest are told to read them (READ_FIRST)."""
    lines = [f"{NAMES[c]} loads each rulebook's copy in `{RULE_FORMATS[c][0]}/` when it reads a matching file."
             for c in loading]
    return " ".join(lines + [READ_FIRST])


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
    prefix = posixpath.relpath(RULES.as_posix(), Path(file_rel).parent.as_posix())  # from the file holding the table
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


TABLE_HEAD = ["| Rulebook | Applies to | Covers |", "|---|---|---|"]


def needs_index(root: Path, file_rel: str, readers: list[str]) -> bool:
    """The file needs the rulebook table, and it is too large to keep inline."""
    ids = _ids(root)
    if all(_loads_itself(root, c, ids) for c in readers):
        return False
    return len("\n".join(TABLE_HEAD + rows(root, file_rel, load_targets(root))).encode("utf-8")) > BLOCK_BUDGET


def render_index(root: Path) -> str:
    """.stackfoundry/rulebooks.md: the rulebook table a large repo keeps out of its instruction files."""
    table = rows(root, INDEX.as_posix(), load_targets(root))
    return "\n".join(["# Rulebooks", "",
                      "<!-- Generated by `stackfoundry render-block`; never edited by hand. -->", "",
                      "Read a rulebook before editing a file that matches its globs.", "", *TABLE_HEAD, *table]) + "\n"


def render(root: Path, file_rel: str, readers: list[str]) -> str:
    template = TEMPLATE.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    _, body, errors = split(template)
    if errors:
        raise ValueError(f"{TEMPLATE.name}: {'; '.join(errors)}")
    targets = load_targets(root)
    ids = _ids(root)
    loading = [c for c in readers if _loads_itself(root, c, ids)]
    if len(loading) == len(readers):
        rulebooks = _scoped(readers)
    else:
        table = rows(root, file_rel, targets)
        if not table:
            raise ProfileError("no rulebooks in .stackfoundry/rules/: write them before the block")
        if needs_index(root, file_rel, readers):
            link = posixpath.relpath(INDEX.as_posix(), Path(file_rel).parent.as_posix())
            told = " ".join(f"{NAMES[c]} loads each rulebook's copy in `{RULE_FORMATS[c][0]}/` when it reads a matching "
                            "file." for c in loading)
            rulebooks = textwrap.fill((told + " " if told else "") +
                                      f"Before editing a file, read [`{INDEX.as_posix()}`]({link}) and every rulebook "
                                      "whose globs match it.", width=117, break_long_words=False,
                                      break_on_hyphens=False)
        else:
            rulebooks = "\n".join([_sentences(loading), "", *TABLE_HEAD, *table])
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


def write_index(root: Path, files: dict[str, list[str]]) -> None:
    """Write .stackfoundry/rulebooks.md when any instruction file links it, and remove it when none does."""
    if any(needs_index(root, rel, readers) for rel, readers in files.items()):
        _write(root, INDEX.as_posix(), render_index(root))
    elif (root / INDEX).is_file():
        (root / INDEX).unlink()
        print(f"removed {INDEX.as_posix()}")


def write(root: Path, file_rel: str, readers: list[str]) -> None:
    path = root / file_rel
    raw = path.read_bytes() if path.is_file() else b""
    crlf = raw.count(b"\r\n") > raw.count(b"\n") // 2 if raw else False
    existing = raw.decode("utf-8-sig").replace("\r\n", "\n") if raw else None
    _write(root, file_rel, splice(existing, render(root, file_rel, readers)), newline="\r\n" if crlf else "\n")


def main(args) -> int:
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    every = files = instruction_files(root, config.load(root)["clients"])
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
        write_index(root, every)  # decided over every instruction file, so one named file never drops another's index
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
