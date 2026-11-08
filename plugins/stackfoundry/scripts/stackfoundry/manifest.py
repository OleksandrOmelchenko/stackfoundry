"""`stackfoundry manifest record|diff|list`: what init generated, from which template, and what changed since.

`.claude/stackfoundry/manifest.lock.json`:
    {"schemaVersion": 1, "pluginVersion": "0.1.0",
     "files": {"<repo-relative path>": {"template": "<plugin-relative path or 'research'>", "templateVersion": "1",
                                        "sha256": "<hex>", "kind": "generated|materialized"}}}

`record` writes the manifest (the one writing subcommand here). `diff` and `list` are read-only.
Template versions come from a `templateVersion:` line in the template's frontmatter (default "1").
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import PLUGIN_ROOT
from .frontmatter import split
from .profile import MANIFEST


def sha256(path: Path) -> str:
    # Hash with line endings normalized, so a checkout with autocrlf does not look like an edit.
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def plugin_version() -> str:
    data = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    return data["version"]


def template_version(template: str) -> str:
    if template in ("", "research"):
        return "research"
    p = PLUGIN_ROOT / template
    if not p.exists():
        return "missing"
    fields, _, _ = split(p.read_text(encoding="utf-8"))
    return str(fields.get("templateVersion", "1"))


def load(root: Path) -> dict:
    p = root / MANIFEST
    if not p.exists():
        return {"schemaVersion": 1, "pluginVersion": plugin_version(), "files": {}}
    return json.loads(p.read_text(encoding="utf-8"))


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
    out = root / MANIFEST
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
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
        outdated = entry.get("kind") != "materialized" and current not in ("research", "missing") \
            and current != entry.get("templateVersion")
        action = (
            "skip (materialized)" if entry.get("kind") == "materialized"
            else "leave deleted" if state == "deleted"
            else "re-research via research-stack" if entry.get("template") == "research"
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
