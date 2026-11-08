"""`stackfoundry verify-plumbing <dir>`: static checks of skill and agent definitions. Read-only.

<dir> is a plugin root (with skills/ and agents/) or a repo root (with .claude/skills and .claude/agents).
Errors exit 1; warnings are printed and do not fail the run.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .frontmatter import split

SKILL_CAP = 250
AGENT_CAP = 300
SKILL_KEYS = {"name", "description", "argument-hint", "disable-model-invocation", "allowed-tools", "model", "paths",
              "when_to_use", "user-invocable", "context", "agent", "version", "license", "effort"}
AGENT_KEYS = {"name", "description", "tools", "model", "color", "disallowedTools", "effort", "permissionMode",
              "maxTurns", "skills", "memory", "isolation", "background"}
KNOWN_TOOLS = {"Read", "Grep", "Glob", "Bash", "PowerShell", "Edit", "Write", "MultiEdit", "NotebookEdit", "WebSearch",
               "WebFetch", "Agent", "Skill", "TodoWrite", "AskUserQuestion", "SendMessage", "Monitor", "LSP"}
# Tools whose mention in an agent's body means the grant must include them.
GATED = ("Agent", "WebSearch", "WebFetch", "Edit", "Write", "PowerShell", "Bash")
NEGATION = re.compile(r"\b(never|not|no|don't|do not|without|cannot|isn't|must not)\b", re.I)
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
PLUGIN_REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s`\"')\]]+)")
SKILL_REF = re.compile(r"/stackfoundry:([a-z0-9-]+)")
AGENT_REF = re.compile(r"subagent_type\s*[:=]\s*[\"'](?:stackfoundry:)?([a-z0-9-]+)[\"']")


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: Path | str, msg: str):
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: Path | str, msg: str):
        self.warnings.append(f"{where}: {msg}")


def layout(base: Path) -> tuple[Path, Path, Path]:
    """(skills dir, agents dir, plugin root used for ${CLAUDE_PLUGIN_ROOT})."""
    if (base / "skills").is_dir() or (base / ".claude-plugin").is_dir():
        return base / "skills", base / "agents", base
    return base / ".claude" / "skills", base / ".claude" / "agents", base


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
            desc = fields.get("description")
            if not isinstance(desc, str) or not desc.strip():
                rep.error(f, "description is missing")
            elif len(desc) > SKILL_CAP:
                rep.error(f, f"description is {len(desc)} characters (cap {SKILL_CAP})")
            for key in fields:
                if key not in SKILL_KEYS:
                    rep.warn(f, f"unknown frontmatter key {key!r}")
            if "disable-model-invocation" in fields and not isinstance(fields["disable-model-invocation"], bool):
                rep.error(f, "disable-model-invocation must be true or false")
            bodies.append((f, body))

    if agents_dir.is_dir():
        for f in sorted(agents_dir.glob("*.md")):
            fields, body, errs = split(f.read_text(encoding="utf-8"))
            for e in errs:
                rep.error(f, f"frontmatter: {e}")
            if not fields:
                rep.error(f, "no frontmatter")
                continue
            agent_names.add(f.stem)
            if fields.get("name") != f.stem:
                rep.error(f, f"name {fields.get('name')!r} does not match the file name {f.stem!r}")
            desc = fields.get("description")
            if not isinstance(desc, str) or not desc.strip():
                rep.error(f, "description is missing")
            elif len(desc) > AGENT_CAP:
                rep.error(f, f"description is {len(desc)} characters (cap {AGENT_CAP})")
            for key in fields:
                if key not in AGENT_KEYS:
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
            for line in body.splitlines():
                if NEGATION.search(line):
                    continue
                for t in GATED:
                    if f"`{t}`" in line and t not in tools:
                        rep.error(f, f"body tells it to use `{t}` but the grant lacks it: {line.strip()[:90]}")
            bodies.append((f, body))

    for path, body in bodies:
        _check_links(path, body, plugin_root, rep)
        for m in SKILL_REF.finditer(body):
            if skill_names and m.group(1) not in skill_names:
                rep.error(path, f"/stackfoundry:{m.group(1)} names a skill that does not exist")
        for m in AGENT_REF.finditer(body):
            if m.group(1) not in agent_names and m.group(1) not in ("Explore", "Plan", "general-purpose"):
                rep.error(path, f"subagent_type {m.group(1)!r} names an agent that does not exist")
    rep.skills = sorted(skill_names)  # type: ignore[attr-defined]
    rep.agents = sorted(agent_names)  # type: ignore[attr-defined]
    return rep


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
