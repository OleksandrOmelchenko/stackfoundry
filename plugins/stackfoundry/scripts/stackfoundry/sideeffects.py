"""`stackfoundry side-effects start|end`: prove an unattended run changed nothing but its report.

`start` records the repo's state; `end` compares and lists every change except the paths `--allow` names (the
report). The state is the git status of every file, untracked ones included, plus the content hash of each file in
the control plane (`.stackfoundry/**`, `.claude/**`, instruction files) and of each file git already lists as
changed or untracked, so an edit to a file that was dirty or untracked before the run is caught too. Works without
git (hashes only).

Writes only its state file, in the system temp folder (outside the repo), and removes it at `end`.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from .gitutil import GitError, run
from .globs import match
from .profile import find_root
from .roles import CONTROL_PLANE

WATCHED = (*CONTROL_PLANE, ".claude/**")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "bin", "obj", "dist", "build", "target"}


def _state_file(root: Path) -> Path:
    key = hashlib.sha256(os.path.normcase(str(root.resolve())).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / "stackfoundry-side-effects" / f"{key}.json"


def _status(root: Path) -> dict[str, str]:
    try:
        out = run(["status", "--porcelain=v1", "-z", "--untracked-files=all"], root)
    except GitError:
        return {}
    status, parts, i = {}, out.split("\0"), 0
    while i < len(parts):
        entry = parts[i]
        i += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        status[path] = code
        if code[0] in "RC":  # a rename names its source next
            i += 1
    return status


def _hash(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _watched(root: Path) -> list[str]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
        for name in filenames:
            rel = name if rel_dir == "." else f"{rel_dir}/{name}"
            if any(match(rel, g) for g in WATCHED):
                found.append(rel)
    return found


def snapshot(root: Path) -> dict:
    status = _status(root)
    paths = set(_watched(root)) | {p for p in status if not p.endswith("/")}
    return {"status": status, "hashes": {p: _hash(root / p) for p in sorted(paths)}}


def compare(before: dict, after: dict, allow: list[str]) -> list[str]:
    changes = []
    for path in sorted(set(before["hashes"]) | set(after["hashes"]) | set(before["status"]) | set(after["status"])):
        if any(match(path, g) for g in allow):
            continue
        b_hash, a_hash = before["hashes"].get(path), after["hashes"].get(path)
        b_code, a_code = before["status"].get(path), after["status"].get(path)
        if path not in before["hashes"] and path not in before["status"]:
            # unseen before: new, unless git tracks it (a clean tracked file only shows once it changes)
            new = a_code is None or a_code == "??" or a_code.startswith("A")
            changes.append(f"{'added' if new else 'removed' if 'D' in a_code else 'changed'}: {path}")
        elif b_hash and not a_hash:
            changes.append(f"removed: {path}")
        elif b_hash != a_hash or b_code != a_code:
            changes.append(f"changed: {path}")
    return changes


def main(args) -> int:
    root = Path(args.root).resolve() if getattr(args, "root", None) else find_root(Path.cwd())
    state = _state_file(root)
    if args.action == "start":
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps(snapshot(root)), encoding="utf-8")
        print(f"side-effects: recorded {root}")
        return 0
    if not state.is_file():
        raise ValueError("no recorded state: run `stackfoundry side-effects start` at the beginning of the run")
    before = json.loads(state.read_text(encoding="utf-8"))
    changes = compare(before, snapshot(root), args.allow or [])
    state.unlink(missing_ok=True)
    if args.json:
        print(json.dumps({"changes": changes}, indent=2))
    else:
        for c in changes:
            print(c)
        print("side-effects: none besides the allowed paths" if not changes
              else f"side-effects: {len(changes)} change(s) besides the allowed paths")
    return 1 if changes else 0
