"""`stackfoundry pack check|render <pack.json>`: validate a researched pack, and render its rulebook.

check   Read-only. Errors exit 1: missing required fields, a citation key with no source, a source without url or
        access date, HTML-escaped text (a sign the JSON went through a renderer), a line break, control character or
        HTML comment in any text (researched text renders inline into always-loaded rulebooks), a rulebook path that
        is not a plain glob, an id whose prefix contradicts its layer. Warnings: an empty section, a rule with no
        `where`, no rulebook paths, a catch-all path, and, in a repo, the signs of text that came from a page rather
        than from research (a URL that is no source, a command to run that is no gate, test or discover command,
        text addressed to an agent). init and research-stack show them to the user.
render  Writes the canonical rulebook (`.stackfoundry/rules/<id>.md`) to stdout, or to --out. Deterministic: the same pack always
        gives the same file, so a re-render after an edit to the pack is a clean diff. The layout is the one
        reference/templates/pack-rulebook.md describes.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

from .cited import DATE, check_cited, check_inline, check_plain_text, check_sources, strings
from .clients import _yaml_plain_or_quoted, _yaml_str
from .profile import find_root

LAYERS = ("language", "app-model", "capability", "tooling")
ID = re.compile(r"^(language|app-model|capability|tooling)-[a-z0-9-]+$")
CITED_SECTIONS = {"rules": ("rule", "why"), "bugCategories": ("name", "lookFor", "failure"), "wiring": (),
                  "performance": (), "security": ()}
# A rulebook path goes into YAML frontmatter and, for some assistants, a comma-joined list.
GLOB_BAD = re.compile(r"[\"'\\,#\s]|: ")
CATCH_ALL = {"*", "**", "**/*", "/**", "**/**", "/**/*"}
URL = re.compile(r"https?://[^\s)\]>`'\"]+")
RUN = re.compile(r"(?i)\b(?:run|execute|invoke|call|pipe to)\s+`([^`]+)`")
ADDRESSED = re.compile(r"(?i)(?:\bignore (?:all |any )?(?:previous|prior|above)\b|\bdisregard\b|\bas an ai\b|"
                       r"\bai assistant\b|\blanguage model\b|\bsystem prompt\b|\byou must\b|\bthe agent must\b)")
PROSE = ("rules", "bugCategories", "wiring", "performance", "security", "testing")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def check(pack: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if pack.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    pid, layer = pack.get("id", ""), pack.get("layer")
    if not ID.fullmatch(pid or ""):
        errors.append(f"id {pid!r} must look like <layer>-<name>")
    if layer not in LAYERS:
        errors.append(f"layer {layer!r} must be one of {', '.join(LAYERS)}")
    elif pid and not pid.startswith(layer + "-"):
        errors.append(f"id {pid!r} does not start with its layer {layer!r}")
    if not DATE.fullmatch(str(pack.get("researchedAt", ""))):
        errors.append("researchedAt must be a YYYY-MM-DD date")
    if not isinstance(pack.get("versions"), list):
        errors.append("versions must be a list (empty when the version is not pinned anywhere)")
    sources = check_sources(pack, errors)
    if not pack.get("rules"):
        errors.append("rules must be a non-empty list")
    for section, required in CITED_SECTIONS.items():
        check_cited(pack.get(section), section, sources, errors, required)
    for i, item in enumerate(pack.get("rules", []) or []):
        if isinstance(item, dict) and item.get("sources") and not item.get("where"):
            warnings.append(f"rules[{i}] has no 'where' (ground it, or say 'not used here yet')")
    check_plain_text(pack, errors)
    check_inline(pack, errors)
    paths = pack.get("rulebookPaths", []) or []
    if not isinstance(paths, list):
        errors.append("rulebookPaths must be a list of globs")
        paths = []
    for i, g in enumerate(paths):
        if not isinstance(g, str) or not g or GLOB_BAD.search(g):
            errors.append(f"rulebookPaths[{i}] must be a plain glob (no quotes, backslashes, commas, '#' or spaces)")
        elif g in CATCH_ALL:
            warnings.append(f"rulebookPaths[{i}] {g!r} loads this rulebook for every file; scope it to the stack")
    for section in ("bugCategories", "testing"):
        if not pack.get(section):
            warnings.append(f"no {section} section")
    if not pack.get("rulebookPaths"):
        warnings.append("no rulebookPaths: the rulebook will load in no session")
    return errors, warnings


def _commands(root: Path) -> tuple[dict, set[str]]:
    """The repo's targets by name, and every command it already trusts: gates, test commands, discover commands."""
    targets, known = {}, set()
    try:
        data = json.loads((root / ".stackfoundry" / "targets.json").read_text(encoding="utf-8-sig"))
        targets = {t.get("name"): t for t in data.get("targets", []) if isinstance(t, dict)}
    except (OSError, ValueError, AttributeError):
        pass
    for t in targets.values():
        for _, text in strings({"gate": t.get("gate"), "tests": t.get("tests")}):
            known.add(text.strip())
    try:
        eco = json.loads((root / ".stackfoundry" / "ecosystems.json").read_text(encoding="utf-8-sig"))
        for _, text in strings(eco.get("ecosystems") if isinstance(eco, dict) else None):
            known.add(text.strip())
    except (OSError, ValueError, AttributeError):
        pass
    return targets, known


def check_context(pack: dict, root: Path) -> list[str]:
    """Warnings that need the repo: signs that text came from a page rather than from research. (A path matching
    no file is `stackfoundry globs-check`'s job.)"""
    warnings: list[str] = []
    _, known = _commands(root)
    sources = [str(s.get("url", "")).rstrip("/") for s in (pack.get("sources") or {}).values() if isinstance(s, dict)]
    for section in PROSE:
        for where, text in strings(pack.get(section), section):
            if where.endswith(".sources") or ".sources[" in where:
                continue
            for url in (u.rstrip(".,;:") for u in URL.findall(text)):
                if not any(url.rstrip("/").startswith(s) or s.startswith(url.rstrip("/")) for s in sources if s):
                    warnings.append(f"{where}: URL {url} is not among the pack's sources")
            for cmd in RUN.findall(text):
                if not any(k == cmd.strip() or k.startswith(cmd.strip() + " ") for k in known):
                    warnings.append(f"{where}: tells someone to run `{cmd}`, which is no gate, test or discover "
                                    "command; confirm it is the stack's own advice")
            if ADDRESSED.search(text):
                warnings.append(f"{where}: text addressed to an agent; confirm it is the stack's own advice")
    return warnings


def _inline(text) -> str:
    """One line: researched text never breaks out of its bullet, table cell or value. Line breaks fold into a space
    and other control characters drop; ordinary spacing is kept, so a clean pack renders unchanged."""
    text = re.sub(r"[ \t]*[\r\n\v\f\x1c-\x1e\x85  ]+[ \t]*", " ", str(text or ""))
    return re.sub(r"[\x00-\x08\x0e-\x1b\x1f\x7f]", "", text)


def _cite(keys) -> str:
    return f" [{', '.join(keys)}]" if keys else ""


def _where(item: dict) -> str:
    where = item.get("where") or []
    return f" Here: {'; '.join(where)}." if where else ""


def _cell(text) -> str:
    return _inline(text).replace("|", "\\|")


def _flat(node):
    """The pack with every string (keys included) on one line, so nothing researched can open a heading, close the
    frontmatter or end a table row in the rendered rulebook, even when `check` was skipped."""
    if isinstance(node, str):
        return _inline(node)
    if isinstance(node, dict):
        return {_inline(k): _flat(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_flat(v) for v in node]
    return node


def render(pack: dict) -> str:
    pack = _flat(pack)
    title = pack.get("title") or pack["id"]
    layer = pack["layer"]
    versions = "; ".join(
        f"{v.get('version')} ({v.get('pinnedIn')})" for v in pack.get("versions", []) or []
    ) or "not pinned"
    description = (f"{title} rulebook ({layer} layer). Researched {pack['researchedAt']}; source pack "
                   f".stackfoundry/packs/{pack['id']}/pack.json.")
    out: list[str] = [
        "---",
        f"description: {_yaml_plain_or_quoted(description)}",
    ]
    if pack.get("covers"):  # optional; render-block falls back to the title (existing rulebooks render unchanged)
        out.append(f"covers: {_yaml_plain_or_quoted(pack['covers'])}")
    out += [
        "paths:",
    ]
    out += [f"  - {_yaml_str(g)}" for g in pack.get("rulebookPaths", [])] or ["  []"]
    out += [
        "---",
        "",
        f"# {title} ({layer})",
        "",
        "<!-- Generated by `stackfoundry pack render` from a researched pack. Each rule cites [key] = a source below.",
        "     Disagree with a rule? Record the repo's way in the pack's repoConvention and re-render, so a refresh keeps",
        "     your decision. -->",
        "",
        f"Applies to: {', '.join(pack.get('targets', [])) or 'see targets.json'}. Versions in use: {versions}.",
    ]

    out += ["", "## Rules", ""]
    for r in pack.get("rules", []):
        span = ""
        if r.get("since") or r.get("until"):
            span = " " + " ".join(x for x in (f"Since {r['since']}." if r.get("since") else "",
                                              f"Until {r['until']}." if r.get("until") else "") if x)
        out.append(f"- **{r['rule']}** {r['why']}{span}{_where(r)}{_cite(r.get('sources'))}")
        if r.get("repoConvention"):
            out.append(f"  This repo: {r['repoConvention']}")

    if pack.get("bugCategories"):
        out += ["", "## Bug categories", "", "| Category | Look for | Failure |", "|---|---|---|"]
        for c in pack["bugCategories"]:
            hint = f" ({c['severityHint']})" if c.get("severityHint") else ""
            out.append(f"| `{c['name']}`{hint} | {_cell(c['lookFor'])} | {_cell(c['failure'])}{_cite(c.get('sources'))} |")

    if pack.get("wiring"):
        out += ["", "## Wiring", ""]
        for w in pack["wiring"]:
            fail = f" Fails as: {w['failure']}." if w.get("failure") else ""
            out.append(f"- {w['check']}{fail}{_where(w)}{_cite(w.get('sources'))}")

    t = pack.get("testing") or {}
    if t:
        out += ["", "## Testing", ""]
        if t.get("layers"):
            out += [t["layers"], ""]
        if t.get("harness"):
            out.append(f"- Harness: {'; '.join(t['harness'])}")
        if t.get("commands"):
            out.append(f"- Run: {'; '.join(f'`{c}`' for c in t['commands'])}")
        if t.get("shuffle"):
            out.append(f"- Shuffled: `{t['shuffle']}`")
        if t.get("mutation"):
            out.append(f"- Mutation: {t['mutation']}")
        for trap in t.get("traps", []) or []:
            out.append(f"- Trap: {trap}")
        if t.get("sources"):
            out.append(f"- Sources:{_cite(t['sources'])}")

    for section, heading in (("performance", "Performance"), ("security", "Security")):
        if pack.get(section):
            out += ["", f"## {heading}", ""]
            out += [f"- {n['note']}{_where(n)}{_cite(n.get('sources'))}" for n in pack[section]]

    u = pack.get("upgrade") or {}
    if u:
        out += ["", "## Upgrades", ""]
        if u.get("pins"):
            out.append(f"- Pinned in: {'; '.join(u['pins'])}")
        if u.get("lockStep"):
            out.append(f"- Moves with: {'; '.join(u['lockStep'])}")
        for label, key in (("Release notes", "releaseNotes"), ("Migration guides", "migrationGuides")):
            if u.get(key):
                out.append(f"- {label}: {' · '.join(u[key])}")
        if u.get("deprecationsInUse"):
            out.append(f"- Deprecated APIs still in use: {'; '.join(u['deprecationsInUse'])}")

    out += ["", "## Sources", ""]
    for key, s in pack.get("sources", {}).items():
        version = f"{s['version']}, " if s.get("version") else ""
        out.append(f"- [{key}] {s.get('title') or s['url']}: {s['url']} ({version}accessed {s['accessed']})")

    if pack.get("notReached"):
        out += ["", "## Not reached", ""] + [f"- {n}" for n in pack["notReached"]]
    return "\n".join(out) + "\n"


def main(args) -> int:
    path = Path(args.pack)
    try:
        pack = load(path)
    except (OSError, ValueError) as exc:
        print(f"pack: cannot read {path}: {exc}", file=sys.stderr)
        return 2
    errors, warnings = check(pack)
    if args.action == "check":
        root = find_root(path.resolve().parent)
        if (root / ".stackfoundry" / "targets.json").is_file():
            warnings += check_context(pack, root)
        if args.json:
            print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
        else:
            for e in errors:
                print(f"error: {e}")
            for w in warnings:
                print(f"warning: {w}")
            print(f"pack {pack.get('id')}: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1 if errors else 0
    if errors:
        for e in errors:
            print(f"pack render: {e}", file=sys.stderr)
        return 1
    text = render(pack)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=f".{out.name}.", dir=str(out.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            os.replace(tmp, out)  # atomic: an interrupted render never leaves a truncated rulebook
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0
