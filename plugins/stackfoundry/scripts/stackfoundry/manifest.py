"""`stackfoundry manifest record|diff|list`: what init generated, from which template, and what changed since.

`.stackfoundry/manifest.lock.json`:
    {"schemaVersion": 1, "pluginVersion": "0.1.0",
     "files": {"<repo-relative path>": {"template": "<plugin path | research | profile>", "templateVersion": "1",
                                        "sha256": "<hex>", "kind": "generated|materialized"}}}

`record` and `forget` write the manifest (the only writing actions here). `diff` and `list` are read-only.
Template versions come from a `templateVersion:` line in the template's frontmatter (default "1"). Two template ids
have no template: `research` (a researched pack and its rulebook, refreshed by research-stack) and `profile` (facts
init wrote from the survey and the interview, such as targets.json, refreshed by sync). A file carrying the
`<!-- stackfoundry:begin` ... `<!-- stackfoundry:end -->` markers (the CLAUDE.md block) is hashed by that block only,
so the team's edits elsewhere in the file are not edits of the generated part.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from . import PLUGIN_ROOT
from .frontmatter import split
from .profile import MANIFEST


NO_TEMPLATE = ("research", "profile")
BLOCK = re.compile(rb"<!-- stackfoundry:begin.*?<!-- stackfoundry:end -->", re.S)


def sha256(path: Path) -> str:
    # Hash with line endings normalized, so a checkout with autocrlf does not look like an edit.
    data = path.read_bytes().replace(b"\r\n", b"\n")
    block = BLOCK.search(data)
    return hashlib.sha256(block.group(0) if block else data).hexdigest()


def write_json(path: Path, data: dict) -> None:
    """Atomic and LF-only: an interrupted run never leaves a truncated manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".manifest-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(data, indent=2) + "\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def plugin_version() -> str:
    data = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8-sig"))
    return data["version"]


def template_version(template: str) -> str:
    if template in ("", *NO_TEMPLATE):
        return template or "research"
    p = PLUGIN_ROOT / template
    if not p.exists():
        return "missing"
    fields, _, _ = split(p.read_text(encoding="utf-8-sig"))
    return str(fields.get("templateVersion", "1"))


def load(root: Path) -> dict:
    p = root / MANIFEST
    if not p.exists():
        return {"schemaVersion": 1, "pluginVersion": plugin_version(), "files": {}}
    return json.loads(p.read_text(encoding="utf-8-sig"))


def record(root: Path, files: list[str], template: str, kind: str) -> dict:
    data = load(root)
    data["pluginVersion"] = plugin_version()
    for rel in files:
        rel = rel.replace("\\", "/")
        path = root / rel
        if not path.is_file():
            raise FileNotFoundError(rel)
        data["files"][rel] = {"template": template, "templateVersion": template_version(template),
                              "sha256": sha256(path), "kind": kind}
    data["files"] = dict(sorted(data["files"].items()))
    write_json(root / MANIFEST, data)
    return data


def forget(root: Path, files: list[str]) -> dict:
    """Drop entries (an un-materialized agent, a file the team now owns outright). Writes the manifest."""
    data = load(root)
    for rel in files:
        data["files"].pop(rel.replace("\\", "/"), None)
    write_json(root / MANIFEST, data)
    return data


def diff(root: Path) -> list[dict]:
    """Per recorded file: deleted | edited | untouched, plus whether its template has a newer version."""
    data = load(root)
    out = []
    for rel, entry in data["files"].items():
        path = root / rel
        if not path.exists():
            state = "deleted"
        elif sha256(path) == entry["sha256"]:
            state = "untouched"
        else:
            state = "edited"
        current = template_version(entry.get("template", ""))
        outdated = entry.get("kind") != "materialized" and current not in (*NO_TEMPLATE, "missing") \
            and current != entry.get("templateVersion")
        action = (
            "skip (materialized)" if entry.get("kind") == "materialized"
            else "leave deleted" if state == "deleted"
            else "re-research via research-stack" if entry.get("template") == "research"
            else "none (profile fact; sync keeps it current)" if entry.get("template") == "profile"
            else "none" if not outdated
            else "replace" if state == "untouched"
            else "three-way merge, ask"
        )
        out.append({"file": rel, "state": state, "kind": entry.get("kind"), "template": entry.get("template"),
                    "recorded": entry.get("templateVersion"), "current": current, "outdated": outdated,
                    "action": action})
    return out


def main(args) -> int:
    root = Path(args.root).resolve()
    if args.action == "record":
        data = record(root, args.files, args.template or "", args.kind)
        print(f"recorded {len(args.files)} file(s); manifest holds {len(data['files'])}")
        return 0
    if args.action == "forget":
        data = forget(root, args.files)
        print(f"forgot {len(args.files)} file(s); manifest holds {len(data['files'])}")
        return 0
    if args.action == "list":
        print(json.dumps(load(root), indent=2))
        return 0
    rows = diff(root)
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            print(f"{r['state']:<9} {r['action']:<32} {r['file']}  ({r['template']} {r['recorded']} -> {r['current']})")
    return 0
