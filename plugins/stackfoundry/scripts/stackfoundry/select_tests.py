"""`stackfoundry select-tests`: the test runs a change set needs, from targets.json. Read-only; runs nothing.

For each touched target, each entry in its `tests` list is selected when
  - the mode is `full`, or a changed file matches a `fullRunTriggers` glob (then every target's tests run); or
  - a changed file matches the entry's `paths` (the test files) or `covers` (the source it exercises); or
  - the entry declares neither, which means "run whenever the target changes".
A changed source file that no selected entry covers is listed as **Uncovered**: untested, or reached in a way the
mapping does not know. Either way it is reported, never hidden.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import gitutil
from .change_targets import classify, resolve_files
from .globs import match_any
from .profile import load_targets


def plan(data: dict, files: list[str], mode: str = "affected") -> dict:
    targets = {t["name"]: t for t in data["targets"]}
    cls = classify(data, files)
    triggers = [f for f in files if match_any(f, data.get("fullRunTriggers", []))]
    effective = "full" if mode == "full" or triggers else "affected"
    reason = (
        "requested" if mode == "full"
        else f"full-run trigger changed: {', '.join(triggers)}" if triggers
        else "only the tests the changed files reach"
    )
    touched = list(targets) if triggers else sorted(cls["targets"])
    runs: list[dict] = []
    uncovered: list[str] = []
    for name in touched:
        target = targets[name]
        entry = cls["targets"].get(name, {"files": [], "testFiles": []})
        changed = entry["files"] + entry["testFiles"]
        covered: set[str] = set()
        for test in target.get("tests", []):
            selectors = test.get("paths", []) + test.get("covers", [])
            hit = [f for f in changed if match_any(f, selectors)] if selectors else changed
            if effective == "full" or hit:
                command = test["command"] if effective == "full" else test.get("affectedCommand", test["command"])
                runs.append({"target": name, "test": test.get("name", "tests"), "kind": test.get("kind", ""),
                             "command": command, "because": hit[:5] if effective != "full" else []})
                covered.update(f for f in entry["files"] if match_any(f, test.get("covers") or target["paths"]))
        uncovered += [f for f in entry["files"] if f not in covered]
    return {"mode": effective, "reason": reason, "runs": runs, "uncovered": uncovered,
            "unmapped": cls["unmapped"], "generated": cls["generated"]}


def render(p: dict) -> str:
    lines = [f"Mode: **{p['mode']}** ({p['reason']})", ""]
    if not p["runs"]:
        lines.append("No test runs selected.")
    for r in p["runs"]:
        why = f"  <- {', '.join(r['because'])}" if r["because"] else ""
        lines.append(f"- [{r['target']}] {r['test']}: `{r['command']}`{why}")
    lines += ["", "Uncovered:" + (" none" if not p["uncovered"] else "")]
    lines += [f"- {f}" for f in p["uncovered"]]
    if p["unmapped"]:
        lines += ["", "Unmapped (no target; judge by hand):"] + [f"- {f}" for f in p["unmapped"]]
    return "\n".join(lines) + "\n"


def main(args) -> int:
    root = Path(args.root).resolve() if args.root else gitutil.repo_root(Path.cwd())
    data = load_targets(root)
    files = resolve_files(root, args.base, args.files)
    p = plan(data, files, args.mode)
    print(json.dumps(p, indent=2) if args.json else render(p), end="" if not args.json else "\n")
    return 0
