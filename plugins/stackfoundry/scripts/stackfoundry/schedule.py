"""`stackfoundry schedule rules <skill>...`: the permission rules a scheduled, unattended run of a skill needs.

An unattended run asks nothing: whatever its rules do not allow is denied (headless `--permission-mode dontAsk`) or
stalls (a desktop scheduled task). So the rules must be complete, and also as narrow as the skill: they are honoured
by every session that reads the same settings file. Each rule comes with its reason.

  - the report folder: `Edit(<docsRoot>/<folder>/**)` (an Edit rule covers Write on the command line);
  - the launcher, exactly as the skills call it, and read-only git;
  - check-updates: each ecosystem's `discover` commands; flaky-watch: each suite's command and shuffled run;
  - the web: tech-radar's `WebSearch`, and `WebFetch(domain:<host>)` only for the hosts the packs name as release
    notes or migration guides (`upgrade.releaseNotes`, `upgrade.migrationGuides`), plus GitHub for the plugin's own
    changelog. Every host a pack happens to cite would be far wider: a shop's own site, an encyclopedia, a placeholder.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from . import PLUGIN_ROOT, config
from .cited import url_host
from .profile import ECOSYSTEMS, PROFILE_DIR, find_root, load_json, load_targets

GITHUB = ("github.com", "raw.githubusercontent.com")
# skill -> (report folder under the docs root, what it reads beyond the repo)
SKILLS = {
    "check-updates": ("dependency-reports", ("discover", "web")),
    "tech-radar": ("radar", ("search", "web")),
    "stackfoundry-radar": ("radar", ("github",)),
    "flaky-watch": ("reports", ("suites",)),
    "docs-reconciler": ("reports", ()),
    "whats-next": ("reports", ()),
}


def launcher() -> str:
    """The launcher path as the skills spell it (`${CLAUDE_PLUGIN_ROOT}` filled in by the host)."""
    root = os.environ.get("CLAUDE_PLUGIN_ROOT") or PLUGIN_ROOT.as_posix()
    return f"{root.rstrip('/')}/scripts/stackfoundry.sh"


def _packs(root: Path) -> list[tuple[str, dict]]:
    out = []
    for path in sorted((root / PROFILE_DIR / "packs").glob("*/pack.json")):
        try:
            out.append((path.parent.name, load_json(path)))
        except (OSError, ValueError):
            continue
    return out


def _web_hosts(root: Path) -> dict[str, str]:
    """host -> reason, from the packs' release-note and migration-guide URLs."""
    hosts: dict[str, list[str]] = {}
    for pid, pack in _packs(root):
        upgrade = pack.get("upgrade") if isinstance(pack.get("upgrade"), dict) else {}
        for key in ("releaseNotes", "migrationGuides"):
            for url in upgrade.get(key, []) or []:
                host = url_host(url)
                if host:
                    hosts.setdefault(host, []).append(f"{pid} {key}")
    out = {}
    for host, refs in sorted(hosts.items()):
        packs = list(dict.fromkeys(r.split()[0] for r in refs))
        named = ", ".join(packs[:3]) + (f" and {len(packs) - 3} more" if len(packs) > 3 else "")
        out[host] = f"release notes or migration guides of {named}"
    return out


def rules(root: Path, skill: str) -> list[dict]:
    """[{"rule", "reason"}] for one skill, in a stable order, without duplicates."""
    if skill not in SKILLS:
        raise ValueError(f"no scheduled skill {skill!r} (one of {', '.join(SKILLS)})")
    folder, reads = SKILLS[skill]
    docs = config.load(root)["docsRoot"].strip("/")
    out = [{"rule": f"Edit({docs}/{folder}/**)", "reason": "the run's one report"},
           {"rule": f'Bash(sh "{launcher()}" *)', "reason": "the stackfoundry launcher, as the skills call it "
                                                            "(side-effects, today, config, backlog)"},
           {"rule": "Bash(git status *)", "reason": "read-only git: the side-effects check"},
           {"rule": "Bash(git log *)", "reason": "read-only git"}]
    if "discover" in reads and (root / ECOSYSTEMS).is_file():
        for eco in load_json(root / ECOSYSTEMS).get("ecosystems", []) or []:
            if eco.get("kind") == "formats":
                continue  # its discover entry names a skill pass (check-formats), not a command
            for cmd in eco.get("discover", []) or []:
                out.append({"rule": f"Bash({cmd} *)" if not cmd.endswith("*") else f"Bash({cmd})",
                            "reason": f"ecosystem {eco.get('id', '?')}: discover"})
    if "suites" in reads:
        for t in load_targets(root).get("targets", []):
            for s in t.get("tests", []) or []:
                for key in ("command", "shuffle"):
                    if s.get(key):
                        out.append({"rule": f"Bash({s[key]} *)", "reason": f"{t['name']} suite {s.get('name') or ''} "
                                                                           f"{key}".replace("  ", " ")})
    if "search" in reads:
        out.append({"rule": "WebSearch", "reason": "finding releases and advisories for the researched packs"})
    if "web" in reads:
        out += [{"rule": f"WebFetch(domain:{h})", "reason": why} for h, why in _web_hosts(root).items()]
    if "web" in reads or "github" in reads:
        out += [{"rule": f"WebFetch(domain:{h})", "reason": "the stackfoundry plugin's manifest and changelog"}
                for h in GITHUB]
    seen, unique = set(), []
    for r in out:
        if r["rule"] not in seen:
            seen.add(r["rule"])
            unique.append(r)
    return unique


def main(args) -> int:
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    skills = args.skills or list(SKILLS)
    data = {s: rules(root, s) for s in skills}
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    for skill, items in data.items():
        print(f"{skill}:")
        for r in items:
            print(f"  {r['rule']}    # {r['reason']}")
    return 0
