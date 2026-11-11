"""What each assistant reads, and the converters that turn stackfoundry's canonical files into its formats.

The one home of the per-assistant mapping in code (reference/clients.md is the prose with sources):
  - `outputs(clients)`: where init and sync write rulebooks, instruction blocks, generated skills and team agents
    for the assistants a repo uses (`stackfoundry outputs`);
  - `render_rule(text, client)`: a canonical rulebook (`.stackfoundry/rules/<id>.md`, frontmatter `description` +
    `paths`) in that assistant's path-scoped format (`stackfoundry render-rule`);
  - `render_agent(text, client)`: a Claude Code agent file in that assistant's agent format
    (`stackfoundry render-agent`; scripts/build_clients.py uses it for the plugin's own agents).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .frontmatter import split
from .profile import PROFILE_DIR, find_root

CLIENTS = ("claude-code", "codex", "copilot", "cursor", "gemini")
CANONICAL_RULES = (PROFILE_DIR / "rules").as_posix()
CANONICAL_AGENTS = (PROFILE_DIR / "agents").as_posix()

# Claude Code tool grant -> Copilot custom-agent tool aliases (docs.github.com, custom agents configuration).
COPILOT_TOOLS = {"Read": "read", "Grep": "search", "Glob": "search", "Bash": "execute", "PowerShell": "execute",
                 "Edit": "edit", "Write": "edit", "MultiEdit": "edit", "NotebookEdit": "edit", "WebSearch": "web",
                 "WebFetch": "web", "Agent": "agent", "TodoWrite": "todo"}
# Claude Code tool grant -> Gemini CLI built-in tools (geminicli.com, tools reference). Gemini subagents cannot
# call subagents, so Agent maps to nothing.
GEMINI_TOOLS = {"Read": ["read_file", "read_many_files"], "Grep": ["grep_search"], "Glob": ["glob", "list_directory"],
                "Bash": ["run_shell_command"], "PowerShell": ["run_shell_command"], "Edit": ["replace"],
                "MultiEdit": ["replace"], "Write": ["write_file"], "NotebookEdit": ["write_file"],
                "WebSearch": ["google_web_search"], "WebFetch": ["web_fetch"], "AskUserQuestion": ["ask_user"],
                "TodoWrite": ["write_todos"], "Agent": []}

# Path-scoped rule formats: folder, file suffix. Codex and Gemini have none; they read the canonical files through
# the table in their instruction file.
RULE_FORMATS = {"claude-code": (".claude/rules", ".md"), "copilot": (".github/instructions", ".instructions.md"),
                "cursor": (".cursor/rules", ".mdc")}
SIBLING_LINK = re.compile(r"\]\(([a-z0-9][a-z0-9-]*)\.md(#[^)\s]*)?\)")  # a link to a rulebook in the same folder
INSTRUCTION_FILES = {"claude-code": "CLAUDE.md", "codex": "AGENTS.md", "copilot": "AGENTS.md", "cursor": "AGENTS.md",
                     "gemini": "GEMINI.md"}
AGENT_FORMATS = {"claude-code": (".claude/agents", ".md"), "codex": (".codex/agents", ".toml"),
                 "copilot": (".github/agents", ".agent.md"), "cursor": (".cursor/agents", ".md"),
                 "gemini": (".gemini/agents", ".md")}


def outputs(clients: list[str]) -> dict:
    """Where each kind of generated file goes for these assistants. Deterministic; no assistant gets a copy another
    one already reads for it."""
    has = set(clients)
    rules = [{"client": c, "folder": RULE_FORMATS[c][0], "suffix": RULE_FORMATS[c][1]}
             for c in CLIENTS if c in has and c in RULE_FORMATS]
    instructions = sorted({INSTRUCTION_FILES[c] for c in has})
    skills = []
    if "claude-code" in has:
        skills.append(".claude/skills")          # also read by Copilot and Cursor
    if has & {"codex", "gemini", "cursor"} or ("copilot" in has and "claude-code" not in has):
        skills.append(".agents/skills")          # the shared Agent Skills folder
    if "copilot" in has and "claude-code" not in has:
        skills.append(".github/skills")          # Copilot's own, while its .agents/skills support is unconfirmed
    agents = []
    if "claude-code" in has:
        agents.append({"client": "claude-code", "folder": AGENT_FORMATS["claude-code"][0],
                       "suffix": AGENT_FORMATS["claude-code"][1]})
    for c in ("codex", "gemini"):
        if c in has:
            agents.append({"client": c, "folder": AGENT_FORMATS[c][0], "suffix": AGENT_FORMATS[c][1]})
    for c in ("copilot", "cursor"):              # both read .claude/agents too
        if c in has and "claude-code" not in has:
            agents.append({"client": c, "folder": AGENT_FORMATS[c][0], "suffix": AGENT_FORMATS[c][1]})
    return {
        "clients": [c for c in CLIENTS if c in has],
        "canonicalRules": CANONICAL_RULES,
        "rules": rules,
        "rulesReadFromInstructions": [c for c in CLIENTS if c in has and c not in RULE_FORMATS],
        "instructions": instructions,
        "skills": skills,
        "canonicalAgents": CANONICAL_AGENTS,
        "agents": agents,
    }


# --- rulebooks -----------------------------------------------------------------------------------------------------

def _yaml_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _yaml_plain_or_quoted(value: str) -> str:
    """A value left plain when YAML reads it back unchanged, else double-quoted. Plain keeps a canonical rulebook
    byte for byte; quoting is only for what YAML would cut or misread (`: `, ` #`, a leading indicator)."""
    if re.search(r": | #|:$|^\s|\s$", value) or value[:1] in tuple("[]{}&*!|>'\"%@`#,?-") or value == "":
        return _yaml_str(value)
    return value


def render_rule(text: str, client: str) -> str:
    """A canonical rulebook (frontmatter `description` and `paths`) in the assistant's path-scoped format."""
    fields, body, errors = split(text)
    if errors or not fields:
        raise ValueError("the rulebook needs frontmatter with description and paths" +
                         (f": {'; '.join(errors)}" if errors else ""))
    paths = fields.get("paths") or []
    if isinstance(paths, str):
        paths = [paths]
    desc = str(fields.get("description", ""))
    if client == "claude-code":
        head = ["---", f"description: {_yaml_plain_or_quoted(desc)}", "paths:"] + [f"  - {_yaml_str(str(p))}"
                                                                                     for p in paths]
    elif client == "copilot":
        head = ["---", f"description: {_yaml_str(desc)}", f"applyTo: {_yaml_str(','.join(paths))}"]
    elif client == "cursor":
        head = ["---", f"description: {_yaml_plain_or_quoted(desc)}", f"globs: {','.join(paths)}", "alwaysApply: false"]
    else:
        raise ValueError(f"{client} has no path-scoped rules; it reads {CANONICAL_RULES}/ through its instruction file")
    # The body is kept byte for byte, so a canonical rulebook already in Claude Code's form renders unchanged. Every
    # assistant's folder sits as deep as the canonical one, so only links to a sibling rulebook (`tooling-x.md`)
    # change: its copy there carries the assistant's suffix.
    suffix = RULE_FORMATS[client][1]
    if suffix != ".md":
        body = SIBLING_LINK.sub(lambda m: f"]({m.group(1)}{suffix}{m.group(2) or ''})", body)
    return "\n".join(head + ["---"]) + "\n" + body.rstrip("\n") + "\n"


def rule_path(src: Path, client: str) -> str:
    folder, suffix = RULE_FORMATS[client]
    return f"{folder}/{src.name.removesuffix('.md')}{suffix}"


# --- agents --------------------------------------------------------------------------------------------------------

def _grant(fields: dict) -> list[str]:
    tools = fields.get("tools", [])
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(",") if t.strip()]
    return list(tools)


def _needs_quotes(value) -> bool:
    return isinstance(value, str) and (value == "" or bool(re.search(r"[:#\[\]{}&*!|>'\"%@`]|^\s|\s$", value)))


def _frontmatter(fields: dict) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            lines.append(f"{key}: [{', '.join(json.dumps(v) for v in value)}]")
        else:
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False) if _needs_quotes(value) else value}")
    return "\n".join(lines + ["---"]) + "\n"


def _toml_string(value: str) -> str:
    if "'''" not in value and not value.startswith("\n"):
        return "'''\n" + value + "'''"
    return json.dumps(value, ensure_ascii=False)  # a TOML basic string accepts JSON's escapes for this text


def render_agent(text: str, client: str) -> str:
    """A Claude Code agent file (frontmatter name, description, tools; body = instructions) for the assistant."""
    fields, body, errors = split(text)
    if errors or not fields.get("name") or not fields.get("description"):
        raise ValueError("the agent needs frontmatter with name and description")
    body = body.lstrip("\n")
    grant = _grant(fields)
    if client in ("claude-code", "cursor"):
        return text if text.endswith("\n") else text + "\n"
    if client == "copilot":
        tools: list[str] = []
        for t in grant:
            # An MCP tool keeps its server: mcp__server__tool -> server/tool, Copilot's form.
            alias = COPILOT_TOOLS.get(t) or (t[5:].replace("__", "/", 1) if t.startswith("mcp__") else None)
            if alias and alias not in tools:
                tools.append(alias)
        if not tools:
            # Copilot reads `tools: []` as "no tools at all" and a missing list as "every tool": neither keeps the
            # source agent's intent, so refuse instead of guessing.
            raise ValueError(f"{fields['name']}: no tool in its grant has a Copilot alias ({', '.join(grant) or 'none'})")
        return _frontmatter({"name": fields["name"], "description": fields["description"], "tools": tools}) + body
    if client == "gemini":
        gtools: list[str] = []
        for t in grant:
            for g in GEMINI_TOOLS.get(t, []):
                if g not in gtools:
                    gtools.append(g)
        return _frontmatter({"name": fields["name"], "description": fields["description"], "kind": "local",
                             "tools": gtools}) + body
    if client == "codex":
        # Codex custom agents: name, description, developer_instructions. A read-only grant becomes a read-only
        # sandbox, since Codex agents have no per-tool grant.
        lines = [f"name = {json.dumps(fields['name'])}",
                 f"description = {json.dumps(str(fields['description']), ensure_ascii=False)}"]
        if not set(grant) & {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
            lines.append('sandbox_mode = "read-only"')
        lines.append(f"developer_instructions = {_toml_string(body.rstrip() + chr(10))}")
        return "\n".join(lines) + "\n"
    raise ValueError(f"unknown client {client!r}")


def agent_path(src: Path, client: str) -> str:
    folder, suffix = AGENT_FORMATS[client]
    return f"{folder}/{src.name.removesuffix('.md')}{suffix}"


# --- CLI -----------------------------------------------------------------------------------------------------------

def _write(root: Path, rel: str, text: str, newline: str = "\n") -> None:
    """Atomic, like `pack render --out`: an interrupted write never leaves a truncated rulebook or agent. Line endings
    are `newline` whatever the platform (LF unless an existing file the caller splices into uses CRLF)."""
    import os
    import tempfile
    out = root / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{out.name}.", dir=str(out.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as fh:
            fh.write(text)
        os.replace(tmp, out)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    print(f"wrote {rel}")


def main_outputs(args) -> int:
    from . import config
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    clients = args.clients.split(",") if args.clients else config.load(root)["clients"]
    unknown = [c for c in clients if c not in CLIENTS]
    if unknown:
        print(f"outputs: unknown client(s) {unknown}; known: {', '.join(CLIENTS)}", file=sys.stderr)
        return 2
    data = outputs(clients)
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    print(f"clients: {', '.join(data['clients'])}")
    print(f"rulebooks: canonical in {data['canonicalRules']}/; copies: "
          + ("; ".join(f"{r['client']} {r['folder']}/<id>{r['suffix']}" for r in data["rules"]) or "none"))
    if data["rulesReadFromInstructions"]:
        print(f"  read through the instruction file by: {', '.join(data['rulesReadFromInstructions'])}")
    print(f"instruction blocks: {', '.join(data['instructions'])}")
    print(f"generated skills: {', '.join(data['skills'])}")
    print(f"team agents: canonical in {data['canonicalAgents']}/; copies: "
          + ("; ".join(f"{a['client']} {a['folder']}/<name>{a['suffix']}" for a in data["agents"]) or "none"))
    return 0


def main_render(args, kind: str) -> int:
    src = Path(args.source)
    text = src.read_text(encoding="utf-8-sig")
    out = render_rule(text, args.client) if kind == "rule" else render_agent(text, args.client)
    if args.write:
        root = Path(args.root).resolve() if args.root else find_root(src.resolve().parent)
        _write(root, rule_path(src, args.client) if kind == "rule" else agent_path(src, args.client), out)
    elif args.out:
        _write(Path.cwd(), args.out, out)
    else:
        sys.stdout.write(out)
    return 0
