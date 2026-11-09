"""`stackfoundry config [key]`: the repo's settings from `.stackfoundry/config.json`, with the defaults filled in.

Read-only. The settings live in the repo, not in one assistant's plugin settings, so every assistant and every
collaborator reads the same values. Schema: reference/schemas/config.schema.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .clients import CLIENTS
from .profile import CONFIG, TARGETS, ProfileError, find_root, load_json

EFFORTS = ("quick", "standard", "thorough")
DEFAULTS = {
    "schemaVersion": 1,
    "clients": ["claude-code"],
    "docsRoot": "docs",
    "researchRefreshDays": 90,
    "defaultEffort": "standard",
}


def check(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schemaVersion", 1) != 1:
        errors.append("schemaVersion must be 1")
    clients = data.get("clients", DEFAULTS["clients"])
    if not isinstance(clients, list) or not clients or any(c not in CLIENTS for c in clients):
        errors.append(f"clients must be a non-empty list of {', '.join(CLIENTS)}")
    docs = data.get("docsRoot", DEFAULTS["docsRoot"])
    if not isinstance(docs, str) or not docs or Path(docs).is_absolute() or ".." in Path(docs).parts:
        errors.append("docsRoot must be a folder relative to the repo root, inside it")
    days = data.get("researchRefreshDays", DEFAULTS["researchRefreshDays"])
    if not isinstance(days, int) or isinstance(days, bool) or not 7 <= days <= 365:
        errors.append("researchRefreshDays must be a whole number from 7 to 365")
    if data.get("defaultEffort", DEFAULTS["defaultEffort"]) not in EFFORTS:
        errors.append(f"defaultEffort must be one of {', '.join(EFFORTS)}")
    unknown = sorted(set(data) - set(DEFAULTS))
    if unknown:
        errors.append(f"unknown key(s): {', '.join(unknown)}")
    return errors


def load(root: Path) -> dict:
    """The effective settings: the file's values over the defaults. A missing file means all defaults."""
    path = root / CONFIG
    try:
        data = load_json(path)
    except FileNotFoundError:
        data = {}
    errors = check(data)
    if errors:
        raise ProfileError(f"{CONFIG.as_posix()}:\n  " + "\n  ".join(errors))
    settings = {**DEFAULTS, **data}
    if "docsRoot" not in data:
        # Profiles written before config.json kept the docs root in targets.json; config.json wins when both do.
        try:
            legacy = load_json(root / TARGETS).get("docsRoot")
        except (FileNotFoundError, ProfileError):
            legacy = None
        if isinstance(legacy, str) and legacy:
            settings["docsRoot"] = legacy
    return settings


def main(args) -> int:
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    settings = load(root)
    if args.key:
        if args.key not in DEFAULTS:
            print(f"config: unknown key {args.key!r}; known: {', '.join(k for k in DEFAULTS if k != 'schemaVersion')}",
                  file=sys.stderr)
            return 2
        value = settings[args.key]
        print(json.dumps(value) if args.json or not isinstance(value, (str, int)) else value)
        return 0
    print(json.dumps(settings, indent=2))
    return 0
