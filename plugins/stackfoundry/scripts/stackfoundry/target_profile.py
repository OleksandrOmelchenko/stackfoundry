"""`stackfoundry gate record|list`: the proof of each target's gate and suite commands, in .stackfoundry/gates.json.

    {"schemaVersion": 1, "targets": {"<target>": {"<command>": "proven" | "failed"}}}

A command missing from the file is `unproven`. The status is keyed by the command's own text, so a command edited in
targets.json reads `unproven` again by itself. No dates are kept: a target profile is a living file, and "proven on
<date>" would go stale silently. `record` is the only writer.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .fsutil import atomic_write
from .profile import PROFILE_DIR, ProfileError, find_root, load_json, load_targets

GATES = PROFILE_DIR / "gates.json"
STATUSES = ("proven", "failed", "unproven")
GATE_KINDS = ("build", "test", "lint")
SUITE_KEYS = ("command", "affectedCommand", "shuffle", "coverage", "mutation")


def commands(target: dict) -> list[str]:
    """Every command of a target that can be proven: its gate's build, test and lint, then each suite's commands."""
    gate = target.get("gate") or {}
    out = [c for kind in GATE_KINDS for c in gate.get(kind, []) or []]
    for suite in target.get("tests", []) or []:
        out += [suite[k] for k in SUITE_KEYS if isinstance(suite.get(k), str) and suite[k]]
    return list(dict.fromkeys(out))


def load_gates(root: Path) -> dict:
    path = root / GATES
    if not path.is_file():
        return {"schemaVersion": 1, "targets": {}}
    data = load_json(path)
    data.setdefault("targets", {})
    return data


def status(gates: dict, target: str, command: str) -> str:
    return (gates.get("targets", {}).get(target) or {}).get(command, "unproven")


def _target(root: Path, name: str) -> dict:
    found = next((t for t in load_targets(root).get("targets", []) if t.get("name") == name), None)
    if found is None:
        raise ProfileError(f"no target named {name!r} in .stackfoundry/targets.json")
    return found


def record(root: Path, target: str, command: str, state: str) -> None:
    if state not in STATUSES:
        raise ProfileError(f"status must be one of {', '.join(STATUSES)}")
    known = commands(_target(root, target))
    if command not in known:
        raise ProfileError(f"{command!r} is not a gate or suite command of {target!r} in targets.json "
                           f"(its commands: {'; '.join(known) or 'none'})")
    data = load_gates(root)
    entries = data["targets"].setdefault(target, {})
    if state == "unproven":
        entries.pop(command, None)
    else:
        entries[command] = state
    data["targets"] = {t: dict(sorted(c.items())) for t, c in sorted(data["targets"].items()) if c}
    atomic_write(root / GATES, json.dumps({"schemaVersion": 1, "targets": data["targets"]}, indent=2) + "\n")


def listing(root: Path) -> list[dict]:
    gates = load_gates(root)
    return [{"target": t["name"], "command": c, "status": status(gates, t["name"], c)}
            for t in load_targets(root).get("targets", []) for c in commands(t)]


def main_gate(args) -> int:
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    if args.action == "record":
        if not args.target or args.command is None or not args.status:
            print("gate record: give a target, --command and --status", file=sys.stderr)
            return 2
        record(root, args.target, args.command, args.status)
        print(f"gate: {args.target}: {args.status}: {args.command}")
        return 0
    rows = listing(root)
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            print(f"{r['target']:<16} {r['status']:<9} {r['command']}")
    return 0
