"""`stackfoundry extensions`: repo-owned changes to plugin skills and agents (format: reference/extensions.md).

`list` and `check` are read-only. `new`, `base`, `merge` and `forget` write only under `.stackfoundry/`: the extension
file they name, its base copy under `.stackfoundry/extensions/.base/`, and `.base/index.json`.

`index.json` is committed, so a cloned repo controls it: no path is taken from it as written. A base copy's path is
derived from its fork file, a plugin source must name a plugin skill or agent, and every path is checked after
resolving links (`_entry_paths`).
"""
from __future__ import annotations

import difflib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import PLUGIN_ROOT
from .frontmatter import split
from .gitutil import GitError, git_exe
from .profile import PROFILE_DIR, TARGETS, ProfileError, find_root, load_json

EXT_DIR = PROFILE_DIR / "extensions"
BASE_DIR = EXT_DIR / ".base"
INDEX = BASE_DIR / "index.json"
MATERIALIZED_DIR = PROFILE_DIR / "agents"
KINDS = ("skills", "agents")
MODES = ("extend", "replace")
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SECTION = re.compile(r"^(Rules|Before|After|Replace|Target)\s*(?::\s*(.+?))?\s*$", re.I)
HEADING = re.compile(r"^(#{2,3})\s+(.+?)\s*#*\s*$")
STEP_LABEL = re.compile(r"^\d+\.\s+\*\*(.+?)\*\*")  # a numbered step written as "3. **Dispatch.** ..."
NUMBER = re.compile(r"^(?:step\s+)?\d+(?:\.\d+)*[.):]?\s+", re.I)
FENCE = re.compile(r"^\s*(```|~~~)")
MERGE_SUFFIX = ".merge.md"
PLUGIN_FILE = re.compile(r"^(skills/[a-z0-9]+(-[a-z0-9]+)*/SKILL\.md|agents/[a-z0-9]+(-[a-z0-9]+)*\.md)$")
FORK_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.md$")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------- text helpers

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def _body(text: str) -> str:
    """The text below the frontmatter, ending in one newline."""
    _, body, _ = split(text)
    return body.strip("\n") + "\n"


def _header(text: str) -> str:
    """The frontmatter block verbatim (with its fences), or '' when there is none."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return ""
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[: i + 1]) + "\n"
    return ""


def norm(heading: str) -> str:
    """An anchor or heading as compared: number prefix, emphasis and case dropped."""
    h = NUMBER.sub("", heading.strip())
    h = re.sub(r"[*_`]", "", h)
    return re.sub(r"\s+", " ", h).strip().rstrip(":.").lower()


def headings(text: str) -> list[str]:
    """The anchors of a skill or agent body, outside code fences, as written (number dropped): `##`/`###` headings
    and numbered steps that open with a bold label (`3. **Dispatch.**` → `Dispatch`)."""
    out, fenced = [], False
    for line in text.split("\n"):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = HEADING.match(line)
        if m:
            out.append(NUMBER.sub("", m.group(2)).strip())
            continue
        s = STEP_LABEL.match(line)
        if s:
            out.append(s.group(1).strip().rstrip(".:").strip())
    return out


def sections(body: str) -> list[tuple[str, str | None, str, int]]:
    """(kind, argument, text, line) per `## ` section of an extend file; text before the first is ignored."""
    out: list[tuple[str, str | None, str, int]] = []
    fenced, current = False, None
    for n, line in enumerate(body.split("\n"), start=1):
        if FENCE.match(line):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            if current:
                out.append(current)
            m = SECTION.match(line[3:].strip())
            kind = m.group(1).capitalize() if m else line[3:].strip()
            current = (kind if m else f"?{kind}", m.group(2) if m else None, "", n)
            continue
        if current:
            current = (current[0], current[1], current[2] + line + "\n", current[3])
    if current:
        out.append(current)
    return out


# ---------------------------------------------------------------- plugin side

def plugin_file(plugin_root: Path, kind: str, name: str) -> Path:
    return plugin_root / ("skills" if kind == "skills" else "agents") / (
        f"{name}/SKILL.md" if kind == "skills" else f"{name}.md")


def plugin_version(plugin_root: Path) -> str:
    try:
        data = json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8-sig"))
        return str(data.get("version", "unknown"))
    except (OSError, ValueError):
        return "unknown"


# ---------------------------------------------------------------- base index

def load_index(root: Path) -> dict:
    path = root / INDEX
    if not path.exists():
        return {"schemaVersion": 1, "files": {}}
    data = load_json(path)
    data.setdefault("files", {})
    return data


def _write(path: Path, text: str, crlf: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\r\n" if crlf else "\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _save_index(root: Path, index: dict) -> None:
    index["files"] = dict(sorted(index["files"].items()))
    _write(root / INDEX, json.dumps(index, indent=2, ensure_ascii=False) + "\n")


def _base_path(fork_rel: str) -> str:
    p = Path(fork_rel)
    sub = "materialized" if p.parent.as_posix() == MATERIALIZED_DIR.as_posix() else p.parent.name
    return (BASE_DIR / sub / p.name).as_posix()


def _fork_ok(rel: object) -> bool:
    """Whether a repo-relative POSIX path names an extension or a materialized agent file, by its text alone."""
    if not isinstance(rel, str) or rel.endswith(MERGE_SUFFIX):
        return False
    allowed = [f"{(EXT_DIR / k).as_posix()}/" for k in KINDS] + [f"{MATERIALIZED_DIR.as_posix()}/"]
    return any(rel.startswith(a) and FORK_NAME.match(rel[len(a):]) for a in allowed)


def _rel(root: Path, file: str) -> str:
    """A fork file as a repo-relative POSIX path, refused unless it is an extension or a materialized agent."""
    p = Path(file)
    p = (p if p.is_absolute() else (Path.cwd() / p)).resolve()
    try:
        rel = p.relative_to(root.resolve()).as_posix()
    except ValueError:
        raise ValueError(f"{file} is not inside {root}") from None
    if not _fork_ok(rel):
        raise ValueError(f"{rel}: not an extension or materialized agent file")
    return rel


def _inside(path: Path, parent: Path) -> bool:
    """Whether `path`, with every link resolved, lies under `parent` (taken as given, already resolved)."""
    try:
        path.resolve().relative_to(parent)
        return True
    except (ValueError, OSError):
        return False


def _source(plugin_root: Path, from_rel: object) -> Path:
    """The plugin file a full copy follows; refused unless it names a plugin skill or agent inside the plugin."""
    if not isinstance(from_rel, str) or not PLUGIN_FILE.match(from_rel):
        raise ValueError(f"source {from_rel!r} is not a plugin skill or agent (skills/<name>/SKILL.md or "
                         "agents/<name>.md)")
    src = plugin_root / from_rel
    if not _inside(src, plugin_root.resolve()):
        raise ValueError(f"source {from_rel!r} resolves outside the plugin")
    return src


def _base(root: Path, fork_rel: object) -> Path:
    """The base copy of a fork file: derived from the fork's path, never read from the index."""
    if not _fork_ok(fork_rel):
        raise ValueError(f"{fork_rel!r} is not an extension or materialized agent file")
    base = root / _base_path(fork_rel)
    if not _inside(base, root.resolve() / BASE_DIR):
        raise ValueError(f"{fork_rel}: its base copy resolves outside {BASE_DIR.as_posix()}/")
    return base


def _entry_paths(root: Path, plugin_root: Path, fork_rel: object, entry: object) -> tuple[Path, Path]:
    """(plugin source, base copy) of one index entry, each bounded; ValueError names what is wrong."""
    if not isinstance(entry, dict):
        raise ValueError(f"{fork_rel}: its index entry is not an object")
    return _source(plugin_root, entry.get("from")), _base(root, fork_rel)


def record_base(root: Path, fork_rel: str, from_rel: str, plugin_root: Path = PLUGIN_ROOT) -> dict:
    """Store the plugin text a full copy was taken from, so a later upgrade can merge three ways."""
    src, base = _source(plugin_root, from_rel), _base(root, fork_rel)
    if not src.is_file():
        raise ValueError(f"{from_rel}: no such file in the plugin")
    _write(base, _body(_read(src)))
    index = load_index(root)
    index["files"][fork_rel] = {"from": from_rel, "version": plugin_version(plugin_root), "base": _base_path(fork_rel)}
    _save_index(root, index)
    return index["files"][fork_rel]


def forget(root: Path, fork_rel: str) -> bool:
    base = _base(root, fork_rel)  # derived, so a planted "base" in the index can never name the file deleted
    index = load_index(root)
    if index["files"].pop(fork_rel, None) is None:
        return False
    base.unlink(missing_ok=True)
    _save_index(root, index)
    return True


# ---------------------------------------------------------------- list / check

def _targets(root: Path) -> set[str] | None:
    path = root / TARGETS
    if not path.exists():
        return None
    try:
        data = load_json(path)
    except ProfileError:
        return None
    return {t.get("name") for t in data.get("targets", []) if isinstance(t, dict)}


def _behind(root: Path, rel: str, entry: dict, plugin_root: Path) -> bool | None:
    try:
        src, base = _entry_paths(root, plugin_root, rel, entry)
    except ValueError:
        return None  # `check` reports the bad entry
    if not src.is_file() or not base.is_file():
        return None
    return _body(_read(src)) != _read(base)


def check(root: Path, plugin_root: Path = PLUGIN_ROOT) -> Report:
    rep = Report()
    index = load_index(root)
    targets = _targets(root)
    for kind in KINDS:
        folder = root / EXT_DIR / kind
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            rel = f.relative_to(root).as_posix()
            if f.name.endswith(MERGE_SUFFIX):
                rep.warnings.append(f"{rel}: an unsettled merge; settle it, then `extensions merge "
                                    f"{rel[: -len(MERGE_SUFFIX)]}.md --resolved`")
                continue
            if f.is_dir() or f.suffix != ".md":
                rep.warnings.append(f"{rel}: not an extension (expected <name>.md)")
                continue
            _check_one(root, plugin_root, kind, f, rel, index, targets, rep)
    for rel, entry in index["files"].items():
        try:
            _, base = _entry_paths(root, plugin_root, rel, entry)
        except ValueError as exc:
            rep.errors.append(f"{INDEX.as_posix()}: refused entry: {exc}; the CLI never writes this, so check who "
                              "committed it before removing the entry by hand")
            continue
        if not (root / rel).is_file():
            rep.warnings.append(f"{rel}: has a base copy but no file; run `extensions forget {rel}`")
            continue
        if not base.is_file():
            rep.errors.append(f"{rel}: its base copy {_base_path(rel)} is missing; upgrades cannot merge it")
        if rel.startswith(f"{MATERIALIZED_DIR.as_posix()}/"):
            rep.rows.append({"file": rel, "kind": "materialized", "extends": entry.get("from"), "mode": "replace",
                             "baseVersion": entry.get("version"), "behind": _behind(root, rel, entry, plugin_root)})
    materialized_dir = root / MATERIALIZED_DIR
    if materialized_dir.is_dir():
        for f in sorted(materialized_dir.glob("*.md")):
            rel = f.relative_to(root).as_posix()
            if rel not in index["files"]:
                rep.warnings.append(f"{rel}: materialized without a base copy, so upgrades cannot merge it; run "
                                    f"`extensions base {rel} --from agents/<role>.md`")
    return rep


def _check_one(root, plugin_root, kind, f, rel, index, targets, rep: Report) -> None:
    text = _read(f)
    fields, body, errs = split(text)
    for e in errs:
        rep.errors.append(f"{rel}: frontmatter: {e}")
    name = f.stem
    extends = fields.get("extends", name)
    mode = fields.get("mode", "extend")
    if extends != name:
        rep.errors.append(f"{rel}: extends {extends!r} must equal the file name {name!r}")
    target = plugin_file(plugin_root, kind, name)
    if not NAME.match(name) or not target.is_file():
        rep.errors.append(f"{rel}: the plugin has no {kind[:-1]} named {name!r}")
        return
    if mode not in MODES:
        rep.errors.append(f"{rel}: mode must be extend or replace, not {mode!r}")
        return
    entry = index["files"].get(rel)
    row = {"file": rel, "kind": kind[:-1], "extends": name, "mode": mode,
           "baseVersion": entry.get("version") if entry else None, "behind": None}
    rep.rows.append(row)
    if mode == "replace":
        if not entry:
            rep.errors.append(f"{rel}: mode replace needs a base copy; recreate it with "
                              f"`extensions new {kind[:-1]} {name} --replace` or record one with `extensions base`")
        else:
            row["behind"] = _behind(root, rel, entry, plugin_root)
            if row["behind"]:
                rep.warnings.append(f"{rel}: the plugin changed {name} since this copy; run `extensions merge {rel}`")
        return
    plugin_heads = headings(_body(_read(target)))
    known = {norm(h): h for h in plugin_heads}
    found = sections(body)
    if not found:
        rep.warnings.append(f"{rel}: no sections, so it changes nothing")
    for sec, arg, content, line in found:
        where = f"{rel}: section line {line}"
        if sec.startswith("?"):
            rep.errors.append(f"{where}: unknown section '## {sec[1:]}' (Rules, Before:, After:, Replace:, Target:)")
            continue
        if sec in ("Before", "After", "Replace"):
            if not arg:
                rep.errors.append(f"{where}: '## {sec}:' needs a heading of {name}")
            elif norm(arg) not in known:
                near = difflib.get_close_matches(norm(arg), list(known), n=1, cutoff=0.4)
                hint = f"; nearest: {known[near[0]]!r}" if near else ""
                rep.errors.append(f"{where}: anchor {arg!r} matches no heading of {name}{hint}")
        elif sec == "Target":
            if not arg:
                rep.errors.append(f"{where}: '## Target:' needs a target name")
            elif targets is None:
                rep.warnings.append(f"{where}: no targets.json to check target {arg!r} against")
            elif arg not in targets:
                rep.errors.append(f"{where}: unknown target {arg!r} (targets.json has {sorted(targets)})")
        elif arg:
            rep.errors.append(f"{where}: '## Rules' takes no argument")
        if not content.strip():
            rep.warnings.append(f"{where}: '## {sec}' is empty")


# ---------------------------------------------------------------- new / merge

def new(root: Path, kind: str, name: str, replace: bool, plugin_root: Path = PLUGIN_ROOT) -> str:
    kind = kind if kind.endswith("s") else kind + "s"
    if kind not in KINDS or not NAME.match(name):
        raise ValueError(f"not a skill or agent name: {kind} {name!r}")
    src = plugin_file(plugin_root, kind, name)
    if not src.is_file():
        raise ValueError(f"the plugin has no {kind[:-1]} named {name!r}")
    rel = (EXT_DIR / kind / f"{name}.md").as_posix()
    if (root / rel).exists():
        raise ValueError(f"{rel} already exists")
    plugin_body = _body(_read(src))
    head = f"---\nextends: {name}\nmode: {'replace' if replace else 'extend'}\n---\n"
    if replace:
        _write(root / rel, head + plugin_body)
        record_base(root, rel, src.relative_to(plugin_root).as_posix(), plugin_root)
    else:
        anchors = ", ".join(f'"{h}"' for h in headings(plugin_body)) or "(none)"
        _write(root / rel, head + f"<!-- Anchors (headings of {name}): {anchors}.\n"
                                  "     Sections: ## Rules, ## Before: <heading>, ## After: <heading>, "
                                  "## Replace: <heading>, ## Target: <target>. -->\n\n## Rules\n\n")
    return rel


def _merge3(ours: str, base: str, theirs: str) -> tuple[str, int]:
    with tempfile.TemporaryDirectory(prefix="sf-merge-") as d:
        paths = []
        for label, text in (("ours", ours), ("base", base), ("theirs", theirs)):
            p = Path(d) / label
            p.write_text(text, encoding="utf-8", newline="\n")
            paths.append(str(p))
        try:
            proc = subprocess.run([git_exe(), "merge-file", "-p", "-L", "repo", "-L", "base", "-L", "plugin", *paths],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        except FileNotFoundError as exc:
            raise GitError("git is not on PATH") from exc
    if proc.returncode < 0 or proc.returncode > 127:
        raise GitError(f"git merge-file failed: {proc.stderr.strip()}")
    return proc.stdout, proc.returncode


def merge(root: Path, fork_rel: str, resolved: bool = False, plugin_root: Path = PLUGIN_ROOT) -> dict:
    """Three-way merge a full copy with the installed plugin. Returns {status, conflicts, file}."""
    index = load_index(root)
    entry = index["files"].get(fork_rel)
    if not entry:
        raise ValueError(f"{fork_rel}: no base copy recorded (only replace extensions and materialized agents merge)")
    src, base_file = _entry_paths(root, plugin_root, fork_rel, entry)
    fork = root / fork_rel
    if not _inside(fork, root.resolve() / PROFILE_DIR):
        raise ValueError(f"{fork_rel}: resolves outside {PROFILE_DIR.as_posix()}/")
    raw = fork.read_bytes().decode("utf-8-sig")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    header = _header(text)
    if not src.is_file():
        raise ValueError(f"{entry['from']}: the plugin no longer has it; keep the copy as the repo's own or delete it")
    theirs = _body(_read(src))
    pending = root / (fork_rel[: -len(".md")] + MERGE_SUFFIX)
    if resolved:
        if not pending.is_file():
            raise ValueError(f"{pending.relative_to(root).as_posix()}: nothing to settle")
        if not _inside(pending, root.resolve() / PROFILE_DIR):
            raise ValueError(f"{pending.relative_to(root).as_posix()}: resolves outside {PROFILE_DIR.as_posix()}/")
        merged = _read(pending)
        if re.search(r"^(<{7}|>{7}) ", merged, re.M):
            raise ValueError(f"{pending.relative_to(root).as_posix()}: still has conflict markers")
        conflicts = 0
    else:
        base = _read(base_file)
        if theirs == base:
            return {"status": "current", "conflicts": 0, "file": fork_rel}
        merged, conflicts = _merge3(text[len(header):] if header else text, base, theirs)
        if conflicts:
            _write(pending, header + merged, crlf)
            return {"status": "conflict", "conflicts": conflicts, "file": pending.relative_to(root).as_posix()}
    _write(fork, (header + merged.lstrip("\n") if header else merged), crlf)
    pending.unlink(missing_ok=True)
    _write(base_file, theirs)
    entry["base"] = _base_path(fork_rel)
    entry["version"] = plugin_version(plugin_root)
    index["files"][fork_rel] = entry
    _save_index(root, index)
    return {"status": "merged", "conflicts": 0, "file": fork_rel}


# ---------------------------------------------------------------- CLI

def main(args) -> int:
    root = Path(args.root).resolve() if getattr(args, "root", None) else find_root(Path.cwd())
    plugin_root = Path(args.plugin_root).resolve() if getattr(args, "plugin_root", None) else PLUGIN_ROOT
    if args.action in ("list", "check"):
        rep = check(root, plugin_root)
        if args.json:
            print(json.dumps({"extensions": rep.rows, "errors": rep.errors, "warnings": rep.warnings},
                             indent=2, ensure_ascii=False))
        elif args.action == "list":
            for r in rep.rows:
                state = {True: "behind the plugin", False: "current", None: "-"}[r["behind"]]
                print(f"{r['mode']:<8} {r['kind']:<12} {r['extends']:<28} {state:<18} {r['file']}")
            if not rep.rows:
                print("no extensions")
        else:
            for e in rep.errors:
                print(f"error: {e}")
            for w in rep.warnings:
                print(f"warning: {w}")
            print(f"extensions: {len(rep.rows)} file(s), {len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
        return 1 if (args.action == "check" and rep.errors) else 0
    if args.action == "new":
        if len(args.names) != 2:
            raise ValueError("usage: extensions new skill|agent <name> [--replace]")
        rel = new(root, args.names[0], args.names[1], args.replace, plugin_root)
        print(f"wrote {rel}")
        return 0
    if len(args.names) != 1:
        raise ValueError(f"usage: extensions {args.action} <file>")
    rel = _rel(root, args.names[0])
    if args.action == "base":
        if not args.source:
            raise ValueError("base needs --from <plugin path>, e.g. agents/bug-hunter.md")
        entry = record_base(root, rel, args.source, plugin_root)
        print(f"recorded the base of {rel} ({entry['from']} {entry['version']})")
        return 0
    if args.action == "forget":
        print(f"forgot {rel}" if forget(root, rel) else f"{rel}: no base copy recorded")
        return 0
    result = merge(root, rel, args.resolved, plugin_root)
    if args.json:
        print(json.dumps(result, indent=2))
    elif result["status"] == "conflict":
        print(f"{result['conflicts']} conflict(s): settle them in {result['file']}, then "
              f"`extensions merge {rel} --resolved`")
    else:
        print(f"{rel}: {result['status']}")
    return 1 if result["status"] == "conflict" else 0
