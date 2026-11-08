"""`stackfoundry change-targets`: map a change set to targets and specialist reviewers. Read-only.

Classification of each changed file, first match wins:
  1. `generated` globs  -> generated (never reviewed or hand-edited; regenerate instead)
  2. `ignored` globs    -> ignored
  3. `rules` in order   -> the rule's targets
  4. target `paths`     -> every target whose paths match (two targets may share a folder: a Vue layer and an SSR layer)
  5. target `testPaths` -> that target, as a test file
  6. otherwise          -> unmapped (judge by hand; add a rule when a path keeps coming back)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import gitutil
from .globs import match_any
from .profile import load_targets

MAX_SCAN_BYTES = 1024 * 1024


def classify(data: dict, files: list[str]) -> dict:
    targets = {t["name"]: t for t in data["targets"]}
    result = {
        "targets": {},
        "generated": [],
        "ignored": [],
        "unmapped": [],
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
        result["unmapped"].append(f)

    for name, entry in result["targets"].items():
        entry["testsOnly"] = not entry["files"] and bool(entry["testFiles"])
    return result


def specialists(data: dict, root: Path, files: list[str]) -> list[dict]:
    out = []
    for spec in data.get("specialists", []):
        hits: list[str] = []
        patterns = [re.compile(p) for p in spec.get("contains", [])]
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


def resolve_files(root: Path, base: str | None, files_arg: str | None) -> list[str]:
    if files_arg:
        return [f.strip().replace("\\", "/") for f in files_arg.split(",") if f.strip()]
    return gitutil.changed_files(root, base)


def render_markdown(result: dict, specs: list[dict], base: str | None) -> str:
    lines = [f"# Change targets ({'against ' + base if base else 'uncommitted tree + untracked'})", ""]
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
                       ("unmapped", "Unmapped (judge by hand)")):
        if result[key]:
            lines += ["", f"## {title}"] + [f"- {f}" for f in result[key]]
    return "\n".join(lines) + "\n"


def main(args) -> int:
    root = Path(args.root).resolve() if args.root else gitutil.repo_root(Path.cwd())
    data = load_targets(root)
    files = resolve_files(root, args.base, args.files)
    result = classify(data, files)
    specs = specialists(data, root, files)
    if args.json:
        print(json.dumps({**result, "specialists": specs, "base": args.base}, indent=2))
    else:
        print(render_markdown(result, specs, args.base), end="")
    return 0
