"""`stackfoundry change-targets`: map a change set to targets and specialist reviewers. Read-only.

Classification of each changed file, first match wins:
  1. `generated` globs  -> generated (never reviewed or hand-edited; regenerate instead)
  2. `ignored` globs    -> ignored
  3. `rules` in order   -> the rule's targets
  4. target `paths`     -> every target whose paths match (two targets may share a folder: a Vue layer and an SSR layer)
  5. target `testPaths` -> that target, as a test file
  6. `fullRunTriggers`  -> fullRun (no one target: a change here runs every target's tests)
  7. a file stackfoundry generated (listed in `.stackfoundry/manifest.lock.json`) -> stackfoundry (refreshed by sync
     or upgrade, not reviewed as product code)
  8. otherwise          -> unmapped (judge by hand; add a rule when a path keeps coming back)

A rule with no targets that takes a file some target's `paths` or `testPaths` also match is reported as
`shadowed`: usually a glob without a slash (`*.md`), which matches at any depth, where a root file (`/*.md`) was meant.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from . import gitutil
from .globs import match_any
from .profile import MANIFEST, load_targets

MAX_SCAN_BYTES = 1024 * 1024


def stackfoundry_files(root: Path) -> set[str]:
    """The files the manifest records as stackfoundry's output (rulebooks and their copies, skills, the profile)."""
    try:
        data = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    files = data.get("files") if isinstance(data, dict) else None
    return set(files) if isinstance(files, dict) else set()


def classify(data: dict, files: list[str], own: set[str] | None = None) -> dict:
    """`own`: the files stackfoundry generated (`stackfoundry_files`)."""
    targets = {t["name"]: t for t in data["targets"]}
    result = {
        "targets": {},
        "generated": [],
        "ignored": [],
        "fullRun": [],
        "stackfoundry": [],
        "unmapped": [],
        "shadowed": [],
    }

    def add(name: str, f: str, is_test: bool):
        entry = result["targets"].setdefault(name, {"files": [], "testFiles": []})
        (entry["testFiles"] if is_test else entry["files"]).append(f)

    for f in files:
        if match_any(f, data.get("generated", [])):
            result["generated"].append(f)
            continue
        if match_any(f, data.get("ignored", [])):
            result["ignored"].append(f)
            continue
        rule = next((r for r in data.get("rules", []) if match_any(f, [r["glob"]])), None)
        if rule is not None:
            for name in rule.get("targets", []):
                add(name, f, match_any(f, targets[name].get("testPaths", [])))
            if not rule.get("targets"):
                result["ignored"].append(f)
                hidden = [n for n, t in targets.items()
                          if match_any(f, t.get("paths", []) + t.get("testPaths", []))]
                if hidden:
                    result["shadowed"].append({"file": f, "rule": rule["glob"], "targets": hidden})
            continue
        test_hits = [n for n, t in targets.items() if match_any(f, t.get("testPaths", []))]
        if test_hits:
            for n in test_hits:
                add(n, f, True)
            continue
        hits = [n for n, t in targets.items() if match_any(f, t.get("paths", []))]
        if hits:
            for n in hits:
                add(n, f, False)
            continue
        if match_any(f, data.get("fullRunTriggers", [])):
            result["fullRun"].append(f)
            continue
        if own and f in own:
            result["stackfoundry"].append(f)
            continue
        result["unmapped"].append(f)

    for name, entry in result["targets"].items():
        entry["testsOnly"] = not entry["files"] and bool(entry["testFiles"])
    return result


def specialists(data: dict, root: Path, files: list[str]) -> list[dict]:
    out = []
    for spec in data.get("specialists", []):
        hits: list[str] = []
        patterns = []
        for p in spec.get("contains", []):
            try:
                patterns.append(re.compile(p))
            except re.error as exc:  # one broken rule must not take the whole mapping down
                print(f"change-targets: specialist {spec['agent']}: skipping invalid regex {p!r} ({exc})",
                      file=sys.stderr)
        for f in files:
            if match_any(f, data.get("generated", [])):
                continue
            if spec.get("paths") and match_any(f, spec["paths"]):
                hits.append(f)
                continue
            if patterns and (not spec.get("scope") or match_any(f, spec["scope"])):
                p = root / f
                try:
                    if p.is_file() and p.stat().st_size <= MAX_SCAN_BYTES:
                        text = p.read_text(encoding="utf-8", errors="replace")
                        if any(rx.search(text) for rx in patterns):
                            hits.append(f)
                except OSError:
                    pass
        if hits:
            out.append({"agent": spec["agent"], "why": spec.get("why", ""), "files": hits})
    return out


def resolve_files(root: Path, base: str | None, files_arg, range_arg: str | None = None,
                  all_files: bool = False) -> list[str]:
    """`files_arg`: a list of values, each a path or a comma-separated list of paths (both forms are accepted).
    `all_files`: every tracked file plus untracked ones not ignored by git, to check a whole profile at once."""
    if all_files:
        return sorted(set(gitutil.tracked_files(root))
                      | set(gitutil.paths(["ls-files", "--others", "--exclude-standard"], root)))
    if files_arg:
        values = [files_arg] if isinstance(files_arg, str) else files_arg
        return [f.strip().replace("\\", "/") for v in values for f in v.split(",") if f.strip()]
    if range_arg:  # a commit range exactly, nothing uncommitted (fix-verify commit mode)
        return gitutil.paths(["diff", "--name-only", gitutil.check_ref(range_arg)], root)
    return gitutil.changed_files(root, base)


def render_markdown(result: dict, specs: list[dict], base: str | None, source: str | None = None) -> str:
    scope = source or (f"against {base}" if base else "uncommitted tree + untracked")
    lines = [f"# Change targets ({scope})", ""]
    if not result["targets"]:
        lines.append("**Targets:** none")
    else:
        lines.append("## Targets")
        for name, entry in sorted(result["targets"].items()):
            note = " (tests only)" if entry["testsOnly"] else ""
            lines.append(f"- **{name}**{note}: {len(entry['files'])} source, {len(entry['testFiles'])} test")
            for f in entry["files"] + entry["testFiles"]:
                lines.append(f"  - {f}")
    lines.append("")
    lines.append("## Specialists")
    if specs:
        for s in specs:
            lines.append(f"- **{s['agent']}**: {s['why']}".rstrip(": "))
            for f in s["files"]:
                lines.append(f"  - {f}")
    else:
        lines.append("- none matched (the scan is a hint: add one by judgment and say why)")
    for key, title in (("generated", "Generated (regenerate, never hand-edit or review)"),
                       ("fullRun", "Full-run triggers (no one target: every target's tests run)"),
                       ("stackfoundry", "stackfoundry's own files (refreshed by sync or upgrade)"),
                       ("unmapped", "Unmapped (judge by hand)")):
        if result.get(key):
            lines += ["", f"## {title}"] + [f"- {f}" for f in result[key]]
    if result.get("shadowed"):
        lines += ["", "## Shadowed (a rule with no targets hides these from targets whose paths match them)"]
        lines += [f"- {s['file']}: rule `{s['rule']}` hides it from {', '.join(s['targets'])}"
                  for s in result["shadowed"]]
        lines.append("  A glob without a slash matches at any depth; anchor root files as `/<name>`.")
    return "\n".join(lines) + "\n"


def main(args) -> int:
    root = Path(args.root).resolve() if args.root else gitutil.repo_root(Path.cwd())
    data = load_targets(root)
    files = resolve_files(root, args.base, args.files, args.range, getattr(args, "all", False))
    result = classify(data, files, stackfoundry_files(root))
    specs = specialists(data, root, files)
    if args.json:
        print(json.dumps({**result, "specialists": specs, "base": args.base}, indent=2))
    else:
        if getattr(args, "all", False):
            source = "every file"
        else:
            source = "the files given" if args.files else (f"range {args.range}" if args.range else None)
        print(render_markdown(result, specs, args.base, source), end="")
    return 0
