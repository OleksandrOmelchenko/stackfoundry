"""`stackfoundry verify-plumbing <dir>`: static checks of skill and agent definitions. Read-only.

<dir> is a plugin root (with skills/ and agents/) or a repo root (with .claude/skills and .claude/agents).
Errors exit 1; warnings are printed and do not fail the run.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import PLUGIN_ROOT, preamble
from .frontmatter import split

MATERIALIZED = Path(".stackfoundry") / "agents"

SKILL_CAP = 250
AGENT_CAP = 300
SKILL_KEYS = {"name", "description", "argument-hint", "disable-model-invocation", "allowed-tools", "model", "paths",
              "when_to_use", "user-invocable", "context", "agent", "version", "license", "effort"}
# The fields Claude Code honours in a plugin agent (plugins/components docs), and the ones it silently ignores there.
AGENT_KEYS = {"name", "description", "model", "effort", "maxTurns", "autoCompactWindow", "tools", "disallowedTools",
              "skills", "memory", "background", "omitClaudeMd", "isolation", "color", "experimental"}
IGNORED_IN_PLUGIN_AGENTS = {"permissionMode", "hooks", "mcpServers", "initialPrompt"}
KNOWN_TOOLS = {"Read", "Grep", "Glob", "Bash", "PowerShell", "Edit", "Write", "MultiEdit", "NotebookEdit", "WebSearch",
               "WebFetch", "Agent", "Skill", "TodoWrite", "AskUserQuestion", "SendMessage", "Monitor", "LSP"}
# Tools whose mention in an agent's body means the grant must include them.
GATED = ("Agent", "WebSearch", "WebFetch", "Edit", "Write", "PowerShell", "Bash")
NEGATION = re.compile(r"\b(never|not|no|don't|do not|without|cannot|isn't|must not)\b", re.I)
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
PLUGIN_REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s`\"')\]]+)")
SKILL_REF = re.compile(r"/stackfoundry:([a-z0-9-]+)")
# Agent Skills (agentskills.io): lowercase letters, digits and single hyphens, at most 64 characters.
PORTABLE_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
AGENT_REF = re.compile(r"subagent_type\s*[:=]\s*[\"'](?:stackfoundry:)?([a-z0-9-]+)[\"']")
# The plain-language trigger every plugin skill's description carries, so a request in words starts it.
TRIGGER = re.compile(r"\bUse (?:for|when|to|after|before)\b")


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: Path | str, msg: str):
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: Path | str, msg: str):
        self.warnings.append(f"{where}: {msg}")


def is_plugin_root(base: Path) -> bool:
    """A plugin root holds .claude-plugin/plugin.json. A marketplace root holds only marketplace.json: it is checked
    as a repo (its .claude/), and each plugin in it separately."""
    return (base / ".claude-plugin" / "plugin.json").is_file()


def layout(base: Path) -> tuple[Path, Path, Path]:
    """(skills dir, agents dir, plugin root used for ${CLAUDE_PLUGIN_ROOT}). In a repo, ${CLAUDE_PLUGIN_ROOT} in a
    materialized agent or a repo skill means the installed plugin (this CLI's), never the repo root."""
    if is_plugin_root(base):
        return base / "skills", base / "agents", base
    return base / ".claude" / "skills", base / ".claude" / "agents", PLUGIN_ROOT


def _tools(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value]
    if isinstance(value, str):
        return [t.strip() for t in value.split(",") if t.strip()]
    return []


def _check_links(path: Path, body: str, plugin_root: Path, rep: Report):
    for m in LINK.finditer(body):
        target = m.group(1)
        if re.match(r"^[a-z]+:", target) or target.startswith("#") or "<" in target or "${" in target:
            continue
        target = target.split("#", 1)[0]
        if target and not (path.parent / target).exists():
            rep.error(path, f"link target does not exist: {target}")
    for m in PLUGIN_REF.finditer(body):
        rel = m.group(1).rstrip(".,;:")
        if any(c in rel for c in "<*{"):
            continue
        if not (plugin_root / rel).exists():
            rep.error(path, f"${{CLAUDE_PLUGIN_ROOT}}/{rel} does not exist")


def check(base: Path) -> Report:
    rep = Report()
    skills_dir, agents_dir, plugin_root = layout(base)
    plugin_mode = is_plugin_root(base)
    skill_names: set[str] = set()
    agent_names: set[str] = set()
    bodies: list[tuple[Path, str]] = []

    if skills_dir.is_dir():
        for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            f = d / "SKILL.md"
            if not f.exists():
                rep.error(d, "skill folder without SKILL.md")
                continue
            fields, body, errs = split(f.read_text(encoding="utf-8"))
            for e in errs:
                rep.error(f, f"frontmatter: {e}")
            if not fields:
                rep.error(f, "no frontmatter")
                continue
            skill_names.add(d.name)
            if fields.get("name") != d.name:
                rep.error(f, f"name {fields.get('name')!r} does not match the folder {d.name!r}")
            if not PORTABLE_NAME.match(d.name) or len(d.name) > 64:
                rep.error(f, "name must be lowercase letters, digits and single hyphens, at most 64 characters "
                             "(the Agent Skills standard other assistants enforce)")
            if plugin_mode and preamble.SKILL not in body:
                rep.error(f, "missing or outdated portable-form preamble under the title (see scripts/stackfoundry/preamble.py)")
            desc = fields.get("description")
            if not isinstance(desc, str) or not desc.strip():
                rep.error(f, "description is missing")
            elif len(desc) > SKILL_CAP:
                rep.error(f, f"description is {len(desc)} characters (cap {SKILL_CAP})")
            if isinstance(desc, str) and re.search(r"[<>]", desc):
                rep.warn(f, "description has < or >, which the skill list shows as HTML entities; use [brackets]")
            for key in fields:
                if key not in SKILL_KEYS:
                    rep.warn(f, f"unknown frontmatter key {key!r}")
            if "disable-model-invocation" in fields and not isinstance(fields["disable-model-invocation"], bool):
                rep.error(f, "disable-model-invocation must be true or false")
            if plugin_mode and fields.get("disable-model-invocation") is True:
                rep.error(f, "disable-model-invocation: true makes the skill slash-only; every plugin skill must start "
                             "from a plain request (say \"Only when asked.\" in the description instead)")
            if plugin_mode and isinstance(desc, str) and desc.strip() and not TRIGGER.search(desc):
                rep.error(f, "description has no plain-language trigger (end it with Use for \"...\", Use when, "
                             "Use to, Use after or Use before)")
            bodies.append((f, body))

    agent_files = sorted(agents_dir.glob("*.md")) if agents_dir.is_dir() else []
    if not plugin_mode and (base / MATERIALIZED).is_dir():
        # The canonical team agents; .claude/agents holds Claude Code's copies of them.
        agent_files += sorted((base / MATERIALIZED).glob("*.md"))
    if agent_files:
        for f in agent_files:
            fields, body, errs = split(f.read_text(encoding="utf-8"))
            for e in errs:
                rep.error(f, f"frontmatter: {e}")
            if not fields:
                rep.error(f, "no frontmatter")
                continue
            agent_names.add(f.stem)
            if fields.get("name") != f.stem:
                rep.error(f, f"name {fields.get('name')!r} does not match the file name {f.stem!r}")
            if plugin_mode and preamble.AGENT not in body:
                rep.error(f, "missing or outdated portable-form preamble under the title (see scripts/stackfoundry/preamble.py)")
            desc = fields.get("description")
            if not isinstance(desc, str) or not desc.strip():
                rep.error(f, "description is missing")
            elif len(desc) > AGENT_CAP:
                rep.error(f, f"description is {len(desc)} characters (cap {AGENT_CAP})")
            for key in fields:
                if key in IGNORED_IN_PLUGIN_AGENTS and plugin_mode:
                    rep.warn(f, f"{key!r} is ignored in a plugin agent (put hooks and MCP servers at plugin level)")
                elif key not in AGENT_KEYS and key not in IGNORED_IN_PLUGIN_AGENTS:
                    rep.warn(f, f"unknown frontmatter key {key!r}")
            tools = _tools(fields.get("tools"))
            if not tools:
                rep.error(f, "no tools: grant (an agent without one inherits every tool)")
            for t in tools:
                if t not in KNOWN_TOOLS and not t.startswith("mcp__"):
                    rep.warn(f, f"unknown tool in grant: {t}")
            if isinstance(desc, str) and re.search(r"\bread-only\b", desc, re.I):
                for t in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                    if t in tools:
                        rep.error(f, f"described as read-only but granted {t}")
            # Tool use is instructed in the `## Tooling` section; prose elsewhere may name a tool without using it.
            in_tooling = False
            for line in body.splitlines():
                if line.startswith("## "):
                    in_tooling = line[3:].strip().lower().startswith("tooling")
                    continue
                if not in_tooling or NEGATION.search(line):
                    continue
                for t in GATED:
                    if f"`{t}`" in line and t not in tools:
                        rep.error(f, f"body tells it to use `{t}` but the grant lacks it: {line.strip()[:90]}")
            bodies.append((f, body))

    for path, body in bodies:
        _check_links(path, body, plugin_root, rep)
        for m in SKILL_REF.finditer(body):
            # In a repo, /stackfoundry:* names the installed plugin's skills, not the repo's own.
            if plugin_mode and skill_names and m.group(1) not in skill_names:
                rep.error(path, f"/stackfoundry:{m.group(1)} names a skill that does not exist")
        for m in AGENT_REF.finditer(body):
            if m.group(1) not in agent_names and m.group(1) not in ("Explore", "Plan", "general-purpose"):
                rep.error(path, f"subagent_type {m.group(1)!r} names an agent that does not exist")
    _check_walkthrough(skills_dir, skill_names, plugin_mode, rep)
    rep.skills = sorted(skill_names)  # type: ignore[attr-defined]
    rep.agents = sorted(agent_names)  # type: ignore[attr-defined]
    return rep


def _check_walkthrough(skills_dir: Path, skill_names: set[str], plugin_mode: bool, rep: Report) -> None:
    """The walkthrough's group table must name every other plugin skill, or a new skill is unreachable from it."""
    f = skills_dir / "walkthrough" / "SKILL.md"
    if not plugin_mode or not f.is_file():
        return
    _, body, _ = split(f.read_text(encoding="utf-8"))
    section = body.split("## The groups", 1)[-1].split("\n## ", 1)[0] if "## The groups" in body else ""
    table = "\n".join(line for line in section.splitlines() if line.startswith("|"))
    named = set(re.findall(r"`([a-z0-9-]+)`", table))
    missing = sorted(skill_names - named - {"walkthrough"})
    if not table:
        rep.error(f, "no '## The groups' table")
    elif missing:
        rep.error(f, "the groups table leaves out " + ", ".join(missing) + " (add each to one group)")
    for name in sorted(named - skill_names):
        rep.error(f, f"the groups table names {name!r}, which is not a skill")


def main(args) -> int:
    rep = check(Path(args.dir))
    if args.json:
        print(json.dumps({"errors": rep.errors, "warnings": rep.warnings, "skills": rep.skills, "agents": rep.agents},
                         indent=2))
    else:
        for e in rep.errors:
            print(f"error: {e}")
        for w in rep.warnings:
            print(f"warning: {w}")
        print(f"verify-plumbing: {len(rep.skills)} skill(s), {len(rep.agents)} agent(s), "
              f"{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    return 1 if rep.errors else 0
