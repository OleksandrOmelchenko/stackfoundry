"""`stackfoundry guard`: the pre-tool hook of every assistant. Reads the hook event on stdin and
`.stackfoundry/guards.json`.

Decisions:
  - an edit or write of a file under a `generated` glob                      -> deny, with how to regenerate it;
  - a shell command matching a `commands` pattern                            -> that entry's decision (deny | ask);
  - a git or gh write (commit, push, pull, config set, gh api -f…) while `git.writes` is "ask" or "deny"
                                                                              -> ask or deny (shellwords reads it).
The guards that apply are the nearest `.stackfoundry/guards.json` above the file being edited (or above the
command's working directory), so a linked worktree or a nested repo is guarded by its own profile. Paths are
normalized first, so `gen/../gen/x` or a relative path still meets the globs.

Each assistant sends a different event and expects a different answer (reference/clients.md). `--client` names it;
without it the event's shape tells. One adapter per assistant turns the event into a call (an edit of some paths,
or a shell command) and turns the decision into that assistant's answer. Where an assistant cannot ask (Codex,
Gemini, Cursor's pre-edit hook), an ask becomes a deny whose reason says to get the user's go-ahead.

No profile, an unreadable profile, an unexpected event or any internal error -> no opinion: a guard must never wedge
a session. For most assistants that is no output; Cursor blocks on empty output, so it gets an explicit allow.
Writes nothing.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import shellwords
from .globs import match
from .profile import GUARDS

# The fallback for a command shellwords cannot split (unbalanced quotes): whole-string patterns.
# A command can start after a separator, a parenthesis, whitespace or an opening quote (sh -c 'git push').
_START = r"""(?:^|[;&|(\s'"`])"""
GIT_WRITE = re.compile(
    _START + r"git(?:\s+-C\s+\S+)?\s+("
    r"commit|push|merge|rebase|reset|revert|cherry-pick|clean|am|apply|restore|"
    r"tag(?!\s+(?:-l|--list|-n|--contains|--points-at))(?=\s|$)|"
    r"stash\s+(?:drop|pop|clear|push|save)|stash(?=\s*(?:$|[;&|]))|"
    r"branch\s+(?:-[dDmMfc]|--delete|--move|--force)|"
    r"checkout\s+(?:--\s|-f\b|-b\b|-B\b|\.)|switch\s+(?:-[cC]\b|--discard-changes)"
    r")\b"
)
GH_WRITE = re.compile(_START + r"gh\s+(?:pr\s+(?:create|merge|close|edit|review|comment)|release\s+(?:create|delete|edit)|"
                      r"repo\s+(?:create|delete|edit)|issue\s+(?:create|close|edit|comment))\b")
# apply_patch envelopes (Codex, Copilot) name every file they touch on these lines.
PATCH_FILE = re.compile(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+?)\s*$", re.M)
SHELL_LABELS = {"Bash", "PowerShell"}


@dataclass
class Call:
    kind: str                      # "edit" or "shell"
    base: Path                     # where relative paths and the command resolve
    paths: list[str] = field(default_factory=list)
    command: str = ""
    shell: str = "Bash"            # Bash or PowerShell: what a `commands[].tools` filter names
    can_ask: bool = True           # False where the assistant has no ask for this event


# --- reading the event ---------------------------------------------------------------------------------------------

def detect(event: dict) -> str:
    if "toolName" in event or "toolArgs" in event:
        return "copilot"
    if "cursor_version" in event or event.get("hook_event_name") in ("preToolUse", "beforeShellExecution"):
        return "cursor"
    if event.get("hook_event_name") == "BeforeTool":
        return "gemini"
    if "turn_id" in event or event.get("tool_name") == "apply_patch":
        return "codex"
    return "claude-code"


def _args(value) -> dict:
    """Tool arguments that may arrive as an object or as a JSON string."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _patch_paths(args: dict) -> list[str]:
    paths: list[str] = []
    for value in args.values():
        if isinstance(value, str):
            paths += PATCH_FILE.findall(value)
    return paths


def _path_keys(args: dict, *keys: str) -> list[str]:
    return [args[k] for k in keys if isinstance(args.get(k), str) and args[k]]


def normalize(event: dict, client: str, project: Path) -> Call | None:
    base = Path(event.get("cwd") or project)
    if client in ("claude-code", "codex"):
        tool, args = event.get("tool_name", ""), _args(event.get("tool_input"))
        if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            return Call("edit", base, _path_keys(args, "file_path", "notebook_path"))
        if tool == "apply_patch":
            return Call("edit", base, _patch_paths(args), can_ask=False)
        if tool in SHELL_LABELS:
            return Call("shell", base, command=args.get("command") or "", shell=tool, can_ask=client != "codex")
        return None
    if client == "copilot":
        tool, args = str(event.get("toolName", "")), _args(event.get("toolArgs"))
        if tool in ("create", "edit", "str_replace_editor", "write"):
            return Call("edit", base, _path_keys(args, "path", "file_path", "filePath"))
        if tool == "apply_patch":
            return Call("edit", base, _patch_paths(args))
        if tool in ("bash", "powershell"):
            return Call("shell", base, command=args.get("command") or "",
                        shell="PowerShell" if tool == "powershell" else "Bash")
        return None
    if client == "cursor":
        roots = event.get("workspace_roots") or []
        base = Path(event.get("cwd") or (roots[0] if roots else project))
        if event.get("hook_event_name") == "beforeShellExecution":
            return Call("shell", base, command=event.get("command") or "")
        tool, args = event.get("tool_name", ""), _args(event.get("tool_input"))
        if tool in ("Write", "Edit", "MultiEdit", "Delete"):
            return Call("edit", base, _path_keys(args, "file_path", "path", "target_file"), can_ask=False)
        if tool == "Shell":
            return Call("shell", Path(args.get("working_directory") or base), command=args.get("command") or "",
                        can_ask=False)
        return None
    if client == "gemini":
        tool, args = event.get("tool_name", ""), _args(event.get("tool_input"))
        if tool in ("write_file", "replace"):
            return Call("edit", base, _path_keys(args, "file_path"), can_ask=False)
        if tool == "run_shell_command":
            where = args.get("dir_path")
            return Call("shell", _absolute(where, base) if where else base, command=args.get("command") or "",
                        can_ask=False)
        return None
    return None


# --- deciding ------------------------------------------------------------------------------------------------------

def _absolute(raw: str, base: Path) -> Path:
    p = Path(raw)
    return Path(os.path.normpath(p if p.is_absolute() else base / p))


def _governing_root(start: Path) -> Path | None:
    """The nearest folder at or above `start` that holds a guards.json."""
    for d in (start, *start.parents):
        if (d / GUARDS).is_file():
            return d
    return None


def _load(root: Path) -> dict | None:
    try:
        data = json.loads((root / GUARDS).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def verdict(call: Call, project: Path) -> tuple[str, str] | None:
    """(deny | ask, reason) or None for no opinion."""
    if call.kind == "edit":
        for raw in call.paths:
            target = _absolute(raw, call.base)
            root = _governing_root(target.parent)
            guards = _load(root) if root else None
            if not guards:
                continue
            rel = _relative(str(target), root)
            if rel is None:
                continue
            for g in guards.get("generated", []):
                if match(rel, g["glob"]):
                    how = g.get("regenerate") or "regenerate it from its source"
                    return "deny", f"{rel} is generated ({g['glob']}); never hand-edit it. {how}."
        return None

    root = _governing_root(Path(os.path.normpath(call.base))) or _governing_root(project)
    guards = _load(root) if root else None
    if not guards:
        return None
    cmd = call.command
    for c in guards.get("commands", []):
        if c.get("tools") and call.shell not in c["tools"]:
            continue
        try:
            if re.search(c["pattern"], cmd):
                # The guard only ever denies or asks: a rule cannot use it to pre-approve a command.
                decision = c.get("decision", "deny")
                if decision not in ("deny", "ask"):
                    decision = "ask"
                return decision, c.get("reason", "blocked by the repo's guards.json")
        except re.error:
            continue
    policy = (guards.get("git") or {}).get("writes", "allow")
    if policy in ("ask", "deny") and _git_or_gh_write(cmd, call.shell):
        reason = (guards.get("git") or {}).get(
            "reason", "git and GitHub writes are the user's call in this repo; run one only when asked for it")
        return policy, reason
    return None


def _git_or_gh_write(cmd: str, shell: str) -> bool:
    """Parsed argv by argv (shellwords); a command that cannot be split falls back to the whole-string patterns."""
    parts = shellwords.segments(cmd, shell)
    if parts is None:
        return bool(GIT_WRITE.search(cmd) or GH_WRITE.search(cmd))
    return any(shellwords.git_write(argv) or shellwords.gh_write(argv) for argv in parts)


def _relative(raw: str | None, project: Path) -> str | None:
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        return os.path.normpath(raw).replace("\\", "/")
    a, b = str(p.resolve()), str(project.resolve())
    if os.name == "nt":
        a_cmp, b_cmp = a.lower(), b.lower()
    else:
        a_cmp, b_cmp = a, b
    if a_cmp == b_cmp or not a_cmp.startswith(b_cmp.rstrip("\\/") + os.sep):
        return None
    return a[len(b.rstrip("\\/")) + 1:].replace("\\", "/")


# --- answering -----------------------------------------------------------------------------------------------------

def answer(client: str, event: dict, decided: tuple[str, str] | None, can_ask: bool = True) -> str | None:
    """The text to print, or None for no output."""
    if decided is None:
        return json.dumps({"permission": "allow"}) if client == "cursor" else None
    kind, reason = decided
    if kind == "ask" and not can_ask:
        kind, reason = "deny", f"needs the user's go-ahead first (this assistant's hook cannot ask): {reason}"
    reason = f"stackfoundry guard: {reason}"
    if client in ("claude-code", "codex"):
        return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": kind,
                                                  "permissionDecisionReason": reason}})
    if client == "copilot":
        return json.dumps({"permissionDecision": kind, "permissionDecisionReason": reason})
    if client == "cursor":
        return json.dumps({"permission": kind, "user_message": reason, "agent_message": reason})
    if client == "gemini":
        return json.dumps({"decision": "deny", "reason": reason})
    return None


def decide(event: dict, project: Path, client: str | None = None) -> str | None:
    client = client or detect(event)
    call = normalize(event, client, project)
    if call is None:
        return answer(client, event, None)
    return answer(client, event, verdict(call, project), call.can_ask)


def check_file(path: Path) -> list[str]:
    """Problems that would make the hook silently ignore a rule (it fails open on them)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return [f"{path}: not found"]
    except ValueError as exc:
        return [f"{path}: invalid JSON ({exc}); the hook ignores the whole file"]
    if not isinstance(data, dict):
        return [f"{path}: the top level must be an object; the hook ignores the whole file"]
    problems = []
    if data.get("schemaVersion") != 1:
        problems.append("schemaVersion must be 1")
    for i, g in enumerate(data.get("generated", [])):
        if not isinstance(g, dict) or not isinstance(g.get("glob"), str):
            problems.append(f"generated[{i}]: needs a 'glob'")
    for i, c in enumerate(data.get("commands", [])):
        if not isinstance(c, dict) or not isinstance(c.get("pattern"), str):
            problems.append(f"commands[{i}]: needs a 'pattern'")
            continue
        try:
            re.compile(c["pattern"])
        except re.error as exc:
            problems.append(f"commands[{i}]: pattern does not compile ({exc}); the hook skips it")
        if c.get("decision", "deny") not in ("deny", "ask"):
            problems.append(f"commands[{i}]: decision must be deny or ask")
        if not c.get("reason"):
            problems.append(f"commands[{i}]: give a reason that says what to do instead")
        if any(t not in SHELL_LABELS for t in c.get("tools", [])):
            problems.append(f"commands[{i}]: tools may only be Bash and PowerShell")
    writes = (data.get("git") or {}).get("writes", "allow")
    if writes not in ("allow", "ask", "deny"):
        problems.append("git.writes must be allow, ask or deny")
    return problems


def _project_dir(event: dict) -> Path:
    roots = event.get("workspace_roots") or []
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("GEMINI_PROJECT_DIR")
                or (roots[0] if roots else None) or event.get("cwd") or os.getcwd())


def main(args) -> int:
    if getattr(args, "check", False):
        root = Path(args.root or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        problems = check_file(root / GUARDS)
        for p in problems:
            print(f"guards.json: {p}")
        print("guards.json: ok" if not problems else f"guards.json: {len(problems)} problem(s)")
        return 1 if problems else 0
    client = getattr(args, "client", None)
    if client == "auto":
        client = None
    try:
        # Hook events arrive as UTF-8 bytes. Text-mode stdin would decode them with the platform code page
        # (cp1252 on Windows) and mangle non-ASCII paths, so a protected file would no longer match its glob.
        event = json.loads(sys.stdin.buffer.read().decode("utf-8-sig") or "{}")
        if not isinstance(event, dict):
            event = {}
        out = decide(event, _project_dir(event), client)
    except Exception:  # noqa: BLE001 - fail open, never wedge the session
        out = json.dumps({"permission": "allow"}) if client == "cursor" else None
    if out:
        print(out)
    return 0
