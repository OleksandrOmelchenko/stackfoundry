"""`stackfoundry render-rulebook <name>`: fill a shared rulebook template (reference/rulebooks/) from the profile.

The shared rulebooks (testing, dependency-bumps, documentation, benchmarking) carry placeholders for repo facts: the
docs root, the deferred-upgrades file, and `paths:` lines listing test paths, pin and lock files, or benchmark
folders. This fills them from `.stackfoundry/targets.json`, `ecosystems.json` and `config.json`, deterministically,
so no one renders a rulebook by hand. Writes only with `--out` or `--write` (the canonical `.stackfoundry/rules/`).

A repo's own additions come from `.stackfoundry/rulebook-additions/<name>.md` (reference/rulebook-additions.md): each
`## <heading>` section is appended at the end of that heading's section of the render, and an `extraPaths:` list in
its frontmatter joins `paths:`. A heading the template does not have is an error naming the nearest one, like an
extension anchor, so a renamed heading never drops an addition silently.
"""
from __future__ import annotations

import difflib
import re
from pathlib import Path

from . import REFERENCE, config
from .clients import _write
from .extensions import FENCE, norm
from .frontmatter import split
from .globs import match
from .pack import BRACES, GLOB_BAD
from .profile import ECOSYSTEMS, PROFILE_DIR, ProfileError, find_root, load_json, load_targets

NAMES = ("testing", "dependency-bumps", "documentation", "benchmarking")
ADDITIONS = PROFILE_DIR / "rulebook-additions"
ADDITION_KEYS = {"extraPaths"}
# {{one "  - \"<glob>\"" line per <what>[, plus "  - \"<extra>\""]}} on a line of its own
LIST = re.compile(r'^\{\{one "  - \\"<glob>\\"" line per (?P<what>.+?)(?:, plus "  - \\"(?P<extra>.+?)\\"")?\}\}$', re.M)
TOOLING_LINKS = "{{one link per tooling pack used for tests}}"


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(i for i in items if i))


def _minimal(globs: list[str]) -> list[str]:
    """Drop a glob another one in the list already covers (`tests/test_x.py` under `tests/**`, `ci.yml` under `*.yml`)."""
    def covered(g: str, h: str) -> bool:
        if g == h:
            return False
        if h.endswith("/**") and g.startswith(h[:-2]):
            return True
        return not re.search(r"[*?\[{]", g) and match(g, h)
    globs = _dedupe(globs)
    return [g for g in globs if not any(covered(g, h) for h in globs)]


def _static_folder(glob: str) -> str:
    """The folder a glob names before its first wildcard: `plugins/x/evals/**` -> `plugins/x/evals`, `**/t.py` -> ``."""
    parts = glob.lstrip("/").split("/")[:-1]
    out: list[str] = []
    for part in parts:
        if any(c in part for c in "*?[{"):
            break
        out.append(part)
    return "/".join(out)


def _globs(what: str, targets: dict, ecosystems: dict) -> list[str]:
    if what.startswith("test path of every target"):
        tests = [g for t in targets["targets"] for g in t.get("testPaths", []) or []]
        # Shared test helpers (`tests/_support.py`) are often routed by a `rules` entry rather than listed in a
        # target's testPaths; take a routed rule glob that lives under a folder a test path names in full. Only the
        # first segment would be too wide: `plugins/x/evals/**` would make every rule under `plugins/` a test helper.
        folders = {d + "/" for g in tests if (d := _static_folder(g))}
        helpers = [r.get("glob", "") for r in targets.get("rules", []) or []
                   if isinstance(r, dict) and r.get("targets")
                   and any(r.get("glob", "").lstrip("/").startswith(f) for f in folders)]
        return _dedupe(tests + helpers)
    if what.startswith("pin file and lock file"):
        out: list[str] = []
        for eco in ecosystems.get("ecosystems", []) or []:
            out += [p.get("file", "") for p in eco.get("pins", []) or [] if isinstance(p, dict)]
            out += list(eco.get("lockFiles", []) or [])
        return _dedupe(out)
    if what.startswith("benchmark project folder"):
        return _dedupe([g for t in targets["targets"] if t.get("benchmarks") for g in t.get("paths", [])])
    raise ValueError(f"unknown list placeholder: line per {what}")


def _tooling_links(targets: dict) -> str:
    packs = _dedupe([p for t in targets["targets"] if t.get("tests") or t.get("testPaths")
                     for p in t.get("packs", []) or [] if p.startswith("tooling-")])
    return ", ".join(f"[{p}]({p}.md)" for p in packs) or "none researched yet"


def addition_path(name: str) -> str:
    return f"{ADDITIONS.as_posix()}/{name}.md"


def _sections(body: str) -> list[tuple[str, int, int]]:
    """(heading, start line, end line) of each `## ` section outside code fences; end is the next `## ` or EOF."""
    lines, out, fenced = body.split("\n"), [], False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced and line.startswith("## "):
            if out:
                out[-1] = (out[-1][0], out[-1][1], i)
            out.append((line[3:].strip(), i, len(lines)))
    return out


def load_additions(root: Path, name: str, rendered: str) -> tuple[list[str], list[tuple[str, str]]]:
    """(extra paths, [(heading of the render, text)]) from the repo's additions file; nothing when there is none.
    Raises ValueError for an unknown key, a bad glob, text before the first section, or a heading the render lacks."""
    rel = addition_path(name)
    path = root / rel
    if not path.is_file():
        return [], []
    fields, body, errors = split(path.read_text(encoding="utf-8-sig").replace("\r\n", "\n"))
    if errors:
        raise ValueError(f"{rel}: frontmatter: {'; '.join(errors)}")
    unknown = sorted(set(fields or {}) - ADDITION_KEYS)
    if unknown:
        raise ValueError(f"{rel}: unknown frontmatter key(s) {', '.join(unknown)} (only extraPaths)")
    extra = (fields or {}).get("extraPaths") or []
    if isinstance(extra, str):
        extra = [extra]
    for g in extra:
        if not isinstance(g, str) or not g or GLOB_BAD.search(g):
            hint = "; split `{a,b}` into one glob per extension" if isinstance(g, str) and BRACES.search(g) else ""
            raise ValueError(f"{rel}: extraPaths entry {g!r} must be a plain glob (no quotes, backslashes, commas, "
                             f"braces, '#' or spaces){hint}")
    _, rbody, _ = split(rendered)
    known = {norm(h): h for h, _, _ in _sections(rbody)}
    found = _sections(body)
    lines = body.split("\n")
    before = "\n".join(lines[: found[0][1]] if found else lines).strip()
    if before:
        raise ValueError(f"{rel}: text before the first `## <heading>` section goes nowhere; put it under a heading")
    out = []
    for heading, start, end in found:
        if norm(heading) not in known:
            near = difflib.get_close_matches(norm(heading), list(known), n=1, cutoff=0.4)
            hint = f"; nearest: {known[near[0]]!r}" if near else ""
            raise ValueError(f"{rel}: line {start + 1}: '## {heading}' matches no heading of the {name} rulebook{hint}")
        text = "\n".join(lines[start + 1:end]).strip("\n")
        if text.strip():
            out.append((known[norm(heading)], text))
    return [g for g in extra if isinstance(g, str)], out


def _add_paths(text: str, extra: list[str]) -> str:
    """The rendered rulebook with `extra` globs joined to its frontmatter `paths:` list (deduplicated, minimal)."""
    lines = text.split("\n")
    if not extra or not lines or lines[0] != "---" or "paths:" not in lines:
        return text
    start = lines.index("paths:") + 1
    end = start
    while end < len(lines) and lines[end].startswith("  - "):
        end += 1
    current = [line[4:].strip().strip('"') for line in lines[start:end]]
    merged = _minimal(current + extra)
    return "\n".join(lines[:start] + [f'  - "{g}"' for g in merged] + lines[end:])


def _splice(text: str, additions: list[tuple[str, str]]) -> str:
    """The rendered rulebook with each addition appended at the end of its heading's section, in file order."""
    if not additions:
        return text
    fm_end = 0
    lines = text.split("\n")
    if lines and lines[0] == "---" and "---" in lines[1:]:
        fm_end = lines.index("---", 1) + 1
    body = lines[fm_end:]
    sections = {h: (s, e) for h, s, e in _sections("\n".join(body))}
    inserts: dict[int, list[str]] = {}
    for heading, add in additions:
        inserts.setdefault(sections[heading][1], []).append(add)
    out: list[str] = []
    for i in range(len(body) + 1):
        if i in inserts:
            while out and not out[-1].strip():
                out.pop()
            for add in inserts[i]:
                out += ["", *add.split("\n")]
            out.append("")
        if i < len(body):
            out.append(body[i])
    return "\n".join(lines[:fm_end] + out)


def render(root: Path, name: str) -> tuple[str, str]:
    """(output path, text) of one shared rulebook."""
    if name not in NAMES:
        raise ValueError(f"no shared rulebook {name!r} (one of {', '.join(NAMES)})")
    template = (REFERENCE / "rulebooks" / f"{name}.md").read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    meta, body, errors = split(template)
    if errors or not meta.get("output"):
        raise ValueError(f"reference/rulebooks/{name}.md: template frontmatter needs output:")
    targets = load_targets(root)
    try:
        ecosystems = load_json(root / ECOSYSTEMS)
    except FileNotFoundError:
        ecosystems = {}
    docs_root = config.load(root)["docsRoot"].rstrip("/")
    deferred = ecosystems.get("deferredFile") or f"{docs_root}/plans/deferred-upgrades.md"
    if name == "benchmarking" and not any(t.get("benchmarks") for t in targets["targets"]):
        raise ProfileError("no target has a benchmarks harness (targets.json → benchmarks): no benchmarking rulebook")

    def fill_list(m: re.Match) -> str:
        globs = _globs(m.group("what"), targets, ecosystems)
        if m.group("extra"):
            globs.append(m.group("extra").replace("{{docsRoot}}", docs_root))
        if not globs:
            raise ProfileError(f"{name}: nothing to list for '{m.group('what')}', so the rulebook would never load")
        return "\n".join(f'  - "{g}"' for g in _minimal(globs))

    text = LIST.sub(fill_list, body.lstrip("\n"))
    text = text.replace(TOOLING_LINKS, _tooling_links(targets))
    text = text.replace("{{docsRoot}}", docs_root).replace("{{deferredFile}}", deferred)
    left = sorted(set(re.findall(r"\{\{[^}]*\}\}", text)))
    if left:
        raise ValueError(f"{name}: unfilled placeholders {left}")
    extra, additions = load_additions(root, name, text)
    text = _splice(_add_paths(text, extra), additions)
    return meta["output"], text.rstrip("\n") + "\n"


def main(args) -> int:
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    out, text = render(root, args.name)
    if args.write:
        _write(root, out, text)
    elif args.out:
        _write(Path.cwd(), args.out, text)
    else:
        print(text, end="")
    return 0
