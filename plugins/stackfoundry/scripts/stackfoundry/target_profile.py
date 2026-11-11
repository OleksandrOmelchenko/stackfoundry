"""`stackfoundry gate record|list` and `render-target`. The gate part: the proof of each target's gate and suite commands, in .stackfoundry/gates.json.

    {"schemaVersion": 1, "targets": {"<target>": {"<command>": "proven" | "failed"}}}

A command missing from the file is `unproven`. The status is keyed by the command's own text, so a command edited in
targets.json reads `unproven` again by itself. No dates are kept: a target profile is a living file, and "proven on
<date>" would go stale silently. `record` is the only writer.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
import textwrap
from pathlib import Path

from .fsutil import atomic_write
from .profile import LAYERS, PROFILE_DIR, ProfileError, find_root, load_json, load_targets

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


# --- render-target ------------------------------------------------------------------------------------------------
#
# A target profile's Stack and Gate sections are facts of the profile (targets.json packs, gate, tests, localUrl, and
# gates.json), so they are rendered between markers under their headings. Everything else in the profile (summary,
# where things are, oracles, emphasis, traps, benchmarks) is the model's and the team's prose and is never touched.

SECTIONS = {"stack": "## Stack", "gate": "## Gate"}
BEGIN = "<!-- stackfoundry:begin target-{name} (rendered by stackfoundry render-target; edit outside the markers) -->"
END = "<!-- stackfoundry:end -->"
RULES_DIR = PROFILE_DIR / "rules"


def _layer(pack_id: str) -> str:
    return next((layer for layer in sorted(LAYERS, key=len, reverse=True) if pack_id.startswith(layer + "-")), "?")


def _stack(root: Path, target: dict) -> str:
    rows = ["| Layer | Pack | Rulebook |", "|---|---|---|"]
    for pid in target.get("packs", []) or []:
        rule = f"[{pid}](../rules/{pid}.md)" if (root / RULES_DIR / f"{pid}.md").is_file() else "not researched yet"
        rows.append(f"| {_layer(pid)} | `{pid}` | {rule} |")
    if len(rows) == 2:
        rows.append("| none | no packs in `targets.json` yet | |")
    return "\n".join(rows)


def _wrap(line: str, indent: str = "") -> str:
    return textwrap.fill(line, width=117, subsequent_indent=indent, break_long_words=False, break_on_hyphens=False)


def _gate(target: dict, gates: dict) -> str:
    name, gate = target["name"], target.get("gate") or {}
    cmds = [c for kind in GATE_KINDS for c in gate.get(kind, []) or []]
    out = ["```sh", *cmds, "```"] if cmds else ["No gate commands in `targets.json` yet."]
    out += ["", "Status:"] + ([f"- `{c}`: {status(gates, name, c)}" for c in cmds] or ["- nothing to prove yet"])
    out += ["", _wrap(f"Preconditions: {'; '.join(gate.get('preconditions') or []) or 'none'}."), "", "Suites:"]
    suites = target.get("tests") or []
    for s in suites:
        parts = [f"`{s['command']}` ({status(gates, name, s['command'])})"]
        parts.append(f"shuffled `{s['shuffle']}` ({status(gates, name, s['shuffle'])})" if s.get("shuffle")
                     else "shuffled run: none recorded")
        parts.append(f"coverage `{s['coverage']}`" if s.get("coverage") else "coverage: none recorded")
        parts.append(f"mutation `{s['mutation']}`" if s.get("mutation")
                     else "mutation: none yet (/stackfoundry:setup-mutation)")
        kind = f" ({s['kind']})" if s.get("kind") else ""
        out.append(_wrap(f"- {s.get('name') or 'suite'}{kind}: " + "; ".join(parts) + ".", "  "))
    if not suites:
        out.append("- none recorded")
    url = target.get("localUrl")
    out += ["", f"Local URL for live repros: {f'`{url}`' if url else 'not served locally'}."]
    return "\n".join(out)


def render(root: Path, name: str) -> dict[str, str]:
    """The body of each rendered section, from targets.json, the rulebooks present and gates.json."""
    target = _target(root, name)
    return {"stack": _stack(root, target), "gate": _gate(target, load_gates(root))}


def _marked(name: str, body: str) -> str:
    return f"{BEGIN.format(name=name)}\n{body.rstrip()}\n{END}"


def splice(text: str, bodies: dict[str, str]) -> str:
    """`text` with each section's marked block replaced. A profile without the markers yet has the body under the
    section's heading (up to the next `## ` heading) replaced once by the marked block; everything else is kept."""
    for name, body in bodies.items():
        new = _marked(name, body)
        marked = re.compile(r"<!-- stackfoundry:begin target-" + name + r"\b.*?<!-- stackfoundry:end -->", re.S)
        if marked.search(text):
            text = marked.sub(lambda _: new, text, count=1)
            continue
        heading = re.compile(r"^" + re.escape(SECTIONS[name]) + r"[ \t]*\n", re.M).search(text)
        if heading is None:
            raise ProfileError(f"the profile has no '{SECTIONS[name]}' heading to render under")
        following = re.compile(r"^## ", re.M).search(text, heading.end())
        tail = text[following.start():] if following else ""
        text = text[:heading.end()] + "\n" + new + "\n" + ("\n" + tail if tail else "")
    return text


def _profile(root: Path, name: str) -> Path:
    target = _target(root, name)
    return root / (target.get("profile") or f".stackfoundry/targets/{name}.md")


def main_render(args) -> int:
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    path = _profile(root, args.target)
    raw = path.read_bytes() if path.is_file() else b""
    if not raw:
        raise ProfileError(f"{path.relative_to(root).as_posix()} does not exist: write the profile from "
                           "reference/templates/target.md first, then render its sections")
    crlf = raw.count(b"\r\n") > raw.count(b"\n") // 2
    before = raw.decode("utf-8-sig").replace("\r\n", "\n")
    after = splice(before, render(root, args.target))
    rel = path.relative_to(root).as_posix()
    if args.write:
        if after != before:
            atomic_write(path, after, "\r\n" if crlf else "\n")
            print(f"wrote {rel}")
        return 0
    try:
        sys.stdout.reconfigure(newline="\n")
    except (AttributeError, ValueError):
        pass
    if args.diff:
        if after == before:
            sys.stdout.write("render-target: no change\n")
            return 0
        lines = difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                     f"a/{rel}", f"b/{rel}")
        sys.stdout.write("".join(line if line.endswith("\n") else line + "\n" for line in lines))
        sys.stdout.write(f"size: {rel} {len(before.encode('utf-8'))} bytes -> {len(after.encode('utf-8'))} bytes\n")
        return 0
    sys.stdout.write(after)
    return 0
