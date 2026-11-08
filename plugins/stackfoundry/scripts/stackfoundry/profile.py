"""Load and check the repo profile under `.claude/stackfoundry/` (schemas: reference/schemas/*.schema.json)."""
from __future__ import annotations

import json
from pathlib import Path

PROFILE_DIR = Path(".claude") / "stackfoundry"
TARGETS = PROFILE_DIR / "targets.json"
GUARDS = PROFILE_DIR / "guards.json"
ECOSYSTEMS = PROFILE_DIR / "ecosystems.json"
MANIFEST = PROFILE_DIR / "manifest.lock.json"

EXPOSURES = {"public", "authenticated", "staff", "internal", "offline"}
LAYERS = {"language", "app-model", "capability", "tooling"}


class ProfileError(ValueError):
    pass


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, ValueError) as exc:
        raise ProfileError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"{path}: the top level must be an object")
    return data


def load_targets(root: Path) -> dict:
    path = root / TARGETS
    if not path.exists():
        raise ProfileError(
            f"{TARGETS.as_posix()} not found under {root}: run /stackfoundry:init (or /stackfoundry:sync) first"
        )
    data = load_json(path)
    errors = check_targets(data)
    if errors:
        raise ProfileError(f"{TARGETS.as_posix()}:\n  " + "\n  ".join(errors))
    return data


def check_targets(data: dict) -> list[str]:
    errors: list[str] = []
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        return ["'targets' must be a non-empty list"]
    names = set()
    for i, t in enumerate(targets):
        where = f"targets[{i}]"
        if not isinstance(t, dict):
            errors.append(f"{where}: must be an object")
            continue
        name = t.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"{where}: 'name' is required")
        elif name in names:
            errors.append(f"{where}: duplicate target name {name!r}")
        else:
            names.add(name)
            where = f"target {name!r}"
        if not _str_list(t.get("paths")) or not t.get("paths"):
            errors.append(f"{where}: 'paths' must be a non-empty list of globs")
        for key in ("testPaths", "packs", "stakes", "roles"):
            if key in t and not _str_list(t[key]):
                errors.append(f"{where}: '{key}' must be a list of strings")
        if "exposure" in t and t["exposure"] not in EXPOSURES:
            errors.append(f"{where}: 'exposure' must be one of {sorted(EXPOSURES)}")
        for j, test in enumerate(t.get("tests", []) or []):
            if not isinstance(test, dict) or not isinstance(test.get("command"), str):
                errors.append(f"{where}: tests[{j}] needs a 'command' string")
    for i, rule in enumerate(data.get("rules", []) or []):
        if not isinstance(rule, dict) or not isinstance(rule.get("glob"), str):
            errors.append(f"rules[{i}]: needs a 'glob' string")
            continue
        unknown = [n for n in rule.get("targets", []) if n not in names]
        if unknown:
            errors.append(f"rules[{i}] ({rule['glob']}): unknown target(s) {unknown}")
    for i, spec in enumerate(data.get("specialists", []) or []):
        if not isinstance(spec, dict) or not isinstance(spec.get("agent"), str):
            errors.append(f"specialists[{i}]: needs an 'agent' string")
    for key in ("generated", "ignored"):
        if key in data and not _str_list(data[key]):
            errors.append(f"'{key}' must be a list of globs")
    return errors


def _str_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def find_root(start: Path) -> Path:
    """The nearest ancestor holding `.claude/stackfoundry/`, else the nearest with `.git`, else `start`."""
    start = start.resolve()
    for d in (start, *start.parents):
        if (d / PROFILE_DIR).is_dir():
            return d
    for d in (start, *start.parents):
        if (d / ".git").exists():
            return d
    return start
