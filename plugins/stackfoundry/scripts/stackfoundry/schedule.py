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

import hashlib
import json
import os
import re
import sys
from pathlib import Path

from . import PLUGIN_ROOT, config
from .cited import url_host
from .fsutil import atomic_write
from .gitutil import GitError, run
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
                if re.search(r"<[^>]+>", cmd):
                    continue  # a pattern with a placeholder (`repos/<owner>/<action>`): the run fills it, no rule can
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
    if args.action == "check":
        result = check(root, args.skills or None)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["ok"] else 1
        for skill, r in result["skills"].items():
            state = "ok" if not (r["missing"] or r["denied"]) else "would be denied"
            print(f"{skill}: {state}")
            print("".join(f"  missing: {x}\n" for x in r["missing"]) + "".join(f"  denied: {x}\n" for x in r["denied"])
                  + "".join(f"  broad: {x['rule']} is allowed only through {x['by']}\n" for x in r["broad"]), end="")
        print("".join(f"stale: {x} (another plugin folder; `stackfoundry schedule rules --rewrite`)\n"
                      for x in result["stale"]), end="")
        return 0 if result["ok"] else 1
    if getattr(args, "rewrite", False):
        for r in rewrite(root):
            print(f"{r['file']}: {len(r['added'])} added, {len(r['removed'])} removed")
        return 0
    if getattr(args, "write", False):
        if not args.skills:
            raise ValueError("--write needs the skills that are scheduled (the rules of the others are removed)")
        r = write(root, args.skills, args.to, args.add, args.remove)
        print(f"{r['file']}: {len(r['added'])} added, {len(r['removed'])} removed")
        print("".join(f"  + {rule}\n" for rule in r["added"]) + "".join(f"  - {rule}\n" for rule in r["removed"]), end="")
        if args.to == "project":
            print("note: .claude/settings.json is committed: every teammate and every session gets these rules")
        return 0
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


# --- writing: rules stackfoundry owns -------------------------------------------------------------------------------
#
# The rules go into the local settings (`.claude/settings.local.json`) by default: they serve this clone's scheduled
# tasks on this machine, and the committed `.claude/settings.json` would hand them to every teammate and session.
# What stackfoundry added is recorded per clone (the repo's git dir, never committed), so a rewrite replaces exactly
# those: a launcher rule naming the previous plugin version goes, a rule nobody needs any more goes, and a rule the
# team wrote is never touched, even when it equals one stackfoundry needs.

SETTINGS = {"local": Path(".claude") / "settings.local.json", "project": Path(".claude") / "settings.json"}


def _state_file(root: Path) -> Path:
    try:
        return Path(run(["rev-parse", "--absolute-git-dir"], root).strip()) / "stackfoundry" / "schedule-rules.json"
    except GitError:
        key = hashlib.sha256(os.path.normcase(str(root.resolve())).encode("utf-8")).hexdigest()[:16]
        return Path.home() / ".stackfoundry" / "schedule" / f"{key}.json"


def load_state(root: Path) -> dict:
    try:
        data = json.loads(_state_file(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write(root: Path, skills: list[str], to: str = "local", add: list[str] | None = None,
          remove: list[str] | None = None) -> dict:
    """Merge the skills' rules (plus `add`) into the destination's `permissions.allow`, replacing what stackfoundry
    owned there before. Returns {"file", "added", "removed"}."""
    if to not in SETTINGS:
        raise ValueError(f"--to must be one of {', '.join(SETTINGS)}")
    state = load_state(root)
    mine = state.get(to) if isinstance(state.get(to), dict) else {}
    extra = [r for r in dict.fromkeys([*(mine.get("extra") or []), *(add or [])]) if r not in (remove or [])]
    needed = list(dict.fromkeys([r["rule"] for s in skills for r in rules(root, s)] + extra))
    path = root / SETTINGS[to]
    raw = path.read_bytes() if path.is_file() else b""
    data = json.loads(raw.decode("utf-8-sig")) if raw.strip() else {}
    if not isinstance(data, dict):
        raise ValueError(f"{SETTINGS[to].as_posix()}: the top level must be an object")
    perms = data.setdefault("permissions", {})
    allow = perms.get("allow") or []
    owned = set(mine.get("rules") or [])
    foreign = [r for r in allow if r not in owned]
    perms["allow"] = foreign + [r for r in needed if r not in foreign]
    added = [r for r in needed if r not in allow]
    removed = [r for r in allow if r in owned and r not in needed]
    crlf = raw.count(b"\r\n") > raw.count(b"\n") // 2 if raw else False
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n", "\r\n" if crlf else "\n")
    state[to] = {"skills": list(skills), "rules": [r for r in needed if r not in foreign], "extra": extra}
    atomic_write(_state_file(root), json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    return {"file": SETTINGS[to].as_posix(), "added": added, "removed": removed}


def rewrite(root: Path) -> list[dict]:
    """Rewrite every destination stackfoundry wrote before, for the skills recorded there: after a plugin update the
    launcher path moves, after a sync the packs' hosts may."""
    return [write(root, entry.get("skills") or [], to) for to, entry in load_state(root).items()
            if to in SETTINGS and isinstance(entry, dict)]


# --- checking: what a scheduled run will actually be allowed ---------------------------------------------------------
#
# Claude Code merges the allow and deny lists of the user's, the project's and the local settings. A rule stackfoundry
# needs is fine when one of them allows it exactly, or through a broader rule (flagged, since that broader rule lets
# far more through for every session). A launcher rule naming another plugin folder is stale: it matches nothing the
# skills run after an update.

BROAD = {"Bash", "Bash(*)", "WebFetch", "Edit", "Edit(**)", "Write", "Write(**)"}
LAUNCHER = re.compile(r'^Bash\(sh "(?P<path>[^"]*/scripts/stackfoundry\.sh)" \*\)$')


def _lists(root: Path, user: Path | None) -> tuple[list[str], list[str]]:
    allow: list[str] = []
    deny: list[str] = []
    for path in (user if user is not None else Path.home() / ".claude" / "settings.json",
                 root / SETTINGS["project"], root / SETTINGS["local"]):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        perms = data.get("permissions") if isinstance(data, dict) else None
        if isinstance(perms, dict):
            allow += [r for r in perms.get("allow") or [] if isinstance(r, str)]
            deny += [r for r in perms.get("deny") or [] if isinstance(r, str)]
    return allow, deny


def _covered_by(needed: str, allow: list[str]) -> str | None:
    """The allow rule that covers `needed`: itself, or a broader rule of the same tool."""
    if needed in allow:
        return needed
    tool = needed.split("(", 1)[0]
    for rule in allow:
        if rule in (tool, f"{tool}(*)") or (tool in ("Edit", "Write") and rule in ("Edit(**)", "Write(**)")):
            return rule
        if tool == "Bash" and rule.startswith("Bash(") and needed.startswith("Bash("):
            prefix = rule[5:-1].removesuffix(":*").removesuffix(" *").removesuffix("*")
            if prefix and needed[5:-1].startswith(prefix):
                return rule
    return None


def check(root: Path, skills: list[str] | None = None, user: Path | None = None) -> dict:
    """Per skill: missing, denied and broadly covered rules; plus stale launcher rules anywhere."""
    if not skills:
        recorded = [s for entry in load_state(root).values() if isinstance(entry, dict) for s in entry.get("skills") or []]
        skills = list(dict.fromkeys(recorded)) or list(SKILLS)
    allow, deny = _lists(root, user)
    current = f'Bash(sh "{launcher()}" *)'
    out = {"skills": {}, "stale": [r for r in allow if LAUNCHER.match(r) and r != current]}
    for skill in skills:
        missing, broad, denied = [], [], []
        for r in rules(root, skill):
            if r["rule"] in deny:
                denied.append(r["rule"])
                continue
            by = _covered_by(r["rule"], allow)
            if by is None:
                missing.append(r["rule"])
            elif by != r["rule"]:
                broad.append({"rule": r["rule"], "by": by})
        out["skills"][skill] = {"missing": missing, "denied": denied, "broad": broad}
    out["ok"] = not any(v["missing"] or v["denied"] for v in out["skills"].values())
    return out
