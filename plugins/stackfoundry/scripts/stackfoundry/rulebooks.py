"""`stackfoundry render-rulebook <name>`: fill a shared rulebook template (reference/rulebooks/) from the profile.

The shared rulebooks (testing, dependency-bumps, documentation, benchmarking) carry placeholders for repo facts: the
docs root, the deferred-upgrades file, and `paths:` lines listing test paths, pin and lock files, or benchmark
folders. This fills them from `.stackfoundry/targets.json`, `ecosystems.json` and `config.json`, deterministically,
so no one renders a rulebook by hand. Writes only with `--out` or `--write` (the canonical `.stackfoundry/rules/`).
"""
from __future__ import annotations

import re
from pathlib import Path

from . import REFERENCE, config
from .clients import _write
from .frontmatter import split
from .globs import match
from .profile import ECOSYSTEMS, ProfileError, find_root, load_json, load_targets

NAMES = ("testing", "dependency-bumps", "documentation", "benchmarking")
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
