"""The guard's role rules: what a stackfoundry subagent may change, judged from the agent that made the call.

Claude Code puts the calling subagent in the hook input as `agent_type`: `stackfoundry:<role>` for a plugin agent,
the bare name for a repo agent (reference/clients.md). The main session sends none and is never judged here, so
init, sync and the user's own work are unaffected. Other assistants send no agent, so these rules do not apply
there and those roles stay bound by their instructions only.

  R1  a read-only role runs a command that changes files in the project (rm, mv, sed -i, a redirect, a git write…)
  R2  a subagent edits a control-plane file (.stackfoundry/**, instruction files) its role does not own
  R3  a role that reads the web writes outside its own output
  R4  a subagent's command changes a control-plane file
Every rule asks; the guard turns an ask into a deny where the assistant cannot ask. It is a guardrail against a
steered or mistaken agent, not a security boundary: a command written to hide itself (python -c …) can pass.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

from . import PLUGIN_ROOT, shellwords
from .frontmatter import split
from .globs import match

PREFIX = "stackfoundry:"
READ_ONLY = re.compile(r"\bread-only\b", re.I)
# The files that steer every later session: the profile, guards, extensions, rulebooks and instruction files.
CONTROL_PLANE = (".stackfoundry/**", "CLAUDE.md", "AGENTS.md", "GEMINI.md", ".github/copilot-instructions.md",
                 ".github/instructions/**", ".cursor/rules/**")
# What a role writes as its job; anything else of the control plane asks.
ROLE_OUTPUTS = {
    "stack-researcher": (".stackfoundry/packs/**",),
    "domain-researcher": (".stackfoundry/domain/**",),
    "web-researcher": (),
    "docs-reconciler": ("CLAUDE.md", "AGENTS.md", "GEMINI.md"),
    "skill-agent-verifier": (".stackfoundry/agents/**", ".stackfoundry/rules/**"),
}
WEB_ROLES = {"stack-researcher", "domain-researcher", "web-researcher"}
FILE_PROGRAMS = {"rm", "rmdir", "mv", "cp", "touch", "mkdir", "ln", "chmod", "chown", "truncate", "tee", "dd",
                 "install", "unlink", "shred", "rsync",
                 # PowerShell cmdlets and their aliases
                 "remove-item", "move-item", "copy-item", "new-item", "set-content", "add-content", "out-file",
                 "rename-item", "clear-content", "ri", "del", "erase", "mi", "move", "cpi", "copy", "ni", "sc", "ac",
                 "rni", "ren"}
NULL_SINKS = {"/dev/null", "nul", "$null", "&1", "&2"}
REDIRECTS = {">", ">>", ">|", "&>", "&>>", ">&"}


@lru_cache(maxsize=64)
def _definition(path: str) -> dict | None:
    try:
        fields, _, _ = split(Path(path).read_text(encoding="utf-8-sig"))
    except OSError:
        return None
    return fields


@lru_cache(maxsize=1)
def _plugin_roles() -> tuple[str, ...]:
    folder = PLUGIN_ROOT / "agents"
    return tuple(sorted((p.stem for p in folder.glob("*.md")), key=len, reverse=True)) if folder.is_dir() else ()


def resolve(agent: str | None, project: Path) -> tuple[str, str, bool] | None:
    """(the agent as named, its plugin role, read-only?) for a stackfoundry agent, else None.
    A plugin agent is `stackfoundry:<role>`; a materialized one is `.stackfoundry/agents/<name>.md`, whose role is
    the plugin role its name ends with."""
    if not agent:
        return None
    if agent.startswith(PREFIX):
        role = agent[len(PREFIX):]
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", role):
            return None
        fields = _definition(str(PLUGIN_ROOT / "agents" / f"{role}.md"))
    else:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", agent):
            return None
        fields = _definition(str(project / ".stackfoundry" / "agents" / f"{agent}.md"))
        role = next((r for r in _plugin_roles() if agent == r or agent.endswith(f"-{r}")), agent)
    if fields is None:
        return None
    return agent, role, bool(READ_ONLY.search(str(fields.get("description", ""))))


def _rel(raw: str, base: Path, project: Path) -> str | None:
    """A path argument relative to the project, or None when it lies outside or cannot be told."""
    if not raw or raw.startswith("-") or raw.startswith("~"):
        return None
    if raw.startswith("$") and not re.match(r"^\$(\{PWD\}|PWD)(/|\\|$)", raw):
        return None
    raw = re.sub(r"^\$(\{PWD\}|PWD)", lambda _: str(base), raw)
    p = Path(raw)
    p = Path(os.path.normpath(p if p.is_absolute() else base / p))
    try:
        a, b = os.path.normcase(str(p.resolve())), os.path.normcase(str(project.resolve()))
    except OSError:
        return None
    if a == b:
        return "."
    if not a.startswith(b.rstrip("\\/") + os.sep):
        return None
    return str(p.resolve())[len(str(project.resolve()).rstrip("\\/")) + 1:].replace("\\", "/")


def _control(rel: str | None) -> bool:
    return rel is not None and any(match(rel, g) for g in CONTROL_PLANE)


def _owned(role: str, rel: str) -> bool:
    return any(match(rel, g) for g in ROLE_OUTPUTS.get(role, ()))


def _changes(argv: list[str]) -> tuple[str, list[str]] | None:
    """(what, path arguments) when one simple command changes files, else None."""
    prog = shellwords.program(argv[0])
    args, targets, i = [], [], 1
    while i < len(argv):  # redirects: `> f`, `>> f`, `2> f`, `&> f`; `2>&1` and null sinks write nothing
        tok = argv[i]
        if tok in REDIRECTS:
            if args and args[-1].isdigit():
                args.pop()  # the file descriptor of `2>`
            target = argv[i + 1] if i + 1 < len(argv) else ""
            if target and not (tok == ">&" and target.isdigit()) and target.lower() not in NULL_SINKS:
                targets.append(target)
            i += 2
            continue
        args.append(tok)
        i += 1
    if prog in FILE_PROGRAMS:
        return prog, [a for a in args if not a.startswith("-")] + targets
    if prog in ("sed", "perl") and any(a.startswith("-i") or a == "--in-place" or (prog == "perl" and
                                                                                    re.match(r"^-\w*i", a))
                                       for a in args):
        return f"{prog} -i", [a for a in args if not a.startswith("-")] + targets
    if shellwords.git_write(argv):
        return "a git write", ["."] + targets
    if targets:
        return "a redirect", targets
    return None


def verdict(kind: str, paths: list[str], command: str, shell: str, base: Path, project: Path,
            agent: str | None) -> tuple[str, str] | None:
    """("ask", reason) when a role rule applies, else None."""
    who = resolve(agent, project)
    if who is None:
        return None
    name, role, read_only = who
    if kind == "edit":
        for raw in paths:
            rel = _rel(raw, base, project)
            if rel is None:
                continue
            if _control(rel) and not _owned(role, rel):
                return "ask", (f"{name} is changing {rel}, part of the stackfoundry control plane that steers every "
                               "later session; allow it only if you asked this agent to change it")
            if role in WEB_ROLES and not _owned(role, rel):
                return "ask", (f"{name} reads the web and writes only its own output; it is writing {rel}. Allow it "
                               "only if you asked for that file")
        return None
    parts = shellwords.segments(command, shell)
    if parts is None:
        return ("ask", f"{name} is read-only and this command could not be read; allow it only if it changes "
                       "nothing") if read_only else None
    for argv in parts:
        changed = _changes(argv) if argv else None
        if not changed:
            continue
        what, targets = changed
        rels = [_rel(t, base, project) for t in targets]
        if any(_control(r) and not _owned(role, r) for r in rels):
            return "ask", (f"{name} is changing the stackfoundry control plane with {what}; allow it only if you "
                           "asked this agent to change it")
        if read_only and any(r is not None for r in rels):
            return "ask", (f"{name} is read-only, and this command changes files in the project ({what}); allow it "
                           "only if you asked for that change")
    return None
