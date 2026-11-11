"""`stackfoundry guard`: the pre-tool hook of every assistant. Reads the hook event on stdin and
`.stackfoundry/guards.json`.

Decisions:
  - an edit or write of a file under a `generated` glob                      -> deny, with how to regenerate it;
  - a shell command matching a `commands` pattern                            -> that entry's decision (deny | ask);
  - a git or gh write (commit, push, pull, config set, gh api -f…) while `git.writes` is "ask" or "deny"
                                                                              -> ask or deny (shellwords reads it);
  - a stackfoundry subagent changing what its role must not (Claude Code names it) -> ask (roles.py).
Every `.stackfoundry/guards.json` above the file being edited (or above the command's working directory), plus the
project root's, applies at once and the strictest answer wins: a nested worktree or sample project adds its own
rules, and an empty, partial or broken nested file cannot lift the rules above it. Paths are normalized first, so
`gen/../gen/x` or a relative path still meets the globs, each relative to the root whose file names it.

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
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import roles, shellwords
from .globs import CASE_INSENSITIVE_FS, match
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
    agent: str | None = None       # the subagent that made the call, where the assistant says (roles.py)


# --- reading the event ---------------------------------------------------------------------------------------------

def detect(event: dict) -> str:
    if "toolCall" in event:
        return "antigravity"
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
        agent = event.get("agent_type") if client == "claude-code" and isinstance(event.get("agent_type"), str) \
            else None
        if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            return Call("edit", base, _path_keys(args, "file_path", "notebook_path"), agent=agent)
        if tool == "apply_patch":
            return Call("edit", base, _patch_paths(args), can_ask=False)
        if tool in SHELL_LABELS:
            return Call("shell", base, command=args.get("command") or "", shell=tool, can_ask=client != "codex",
                        agent=agent)
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
    if client == "antigravity":
        # toolCall.{name,args}, PascalCase arguments; no cwd field, and the hook runs from the plugin root, so paths
        # resolve against the workspace (reference/clients.md, [ag-hooks]).
        call = event.get("toolCall") if isinstance(event.get("toolCall"), dict) else {}
        tool, args = str(call.get("name", "")), _args(call.get("args"))
        roots = event.get("workspacePaths") or []
        base = Path(roots[0]) if roots and isinstance(roots[0], str) else project
        if tool in ("write_to_file", "replace_file_content", "multi_replace_file_content"):
            return Call("edit", base, _path_keys(args, "TargetFile"))
        if tool == "run_command":
            where = args.get("Cwd")
            return Call("shell", _absolute(where, base) if isinstance(where, str) and where else base,
                        command=args.get("CommandLine") or "")
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


def _chain(start: Path, project: Path) -> list[tuple[Path, dict]]:
    """Every guards.json that governs `start`, nearest first: each folder at or above it that holds one, plus the
    project root's. A file that does not load, or is empty, is skipped, so it can never switch the others off."""
    chain = []
    for r in _roots(start, project):
        guards = _load(r)
        if guards:
            chain.append((r, guards))
    return chain


def _roots(start: Path, project: Path) -> list[Path]:
    roots = [d for d in (start, *start.parents) if (d / GUARDS).is_file()]
    if (project / GUARDS).is_file() and not any(_same(project, r) for r in roots):
        roots.append(project)
    return roots


def _unreadable_warning(event: dict, start: Path, project: Path) -> str | None:
    """A warning for the user when a governing guards.json cannot be read, so its rules are silently off (the hook
    fails open by design). Once per file version and session: a marker in the temp folder remembers it was said. The
    marker is created exclusively and never through a symlink, so a planted link cannot make it touch another file."""
    import hashlib
    import tempfile

    fresh = []
    for root in _roots(start, project):
        path = root / GUARDS
        if _load(root) is not None:
            continue
        try:
            stamp = f"{event.get('session_id', '')}|{path}|{path.stat().st_mtime_ns}"
        except OSError:
            continue
        marker = Path(tempfile.gettempdir()) / f"stackfoundry-guard-warned-{hashlib.sha256(stamp.encode()).hexdigest()[:16]}"
        if os.path.lexists(marker):  # a dangling symlink counts; Windows has no O_NOFOLLOW and follows it
            continue
        try:
            os.close(os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600))
        except FileExistsError:
            continue  # already said this session
        except OSError:
            pass  # cannot remember it: say it anyway
        fresh.append(str(path))
    if not fresh:
        return None
    return (f"stackfoundry guard: {', '.join(fresh)} cannot be read, so its rules are off. "
            "Run `stackfoundry guard --check` to see why.")


def _same(a: Path, b: Path) -> bool:
    try:
        return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))
    except OSError:
        return False


def _load(root: Path) -> dict | None:
    try:
        data = json.loads((root / GUARDS).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


STRICTNESS = {"allow": 0, "ask": 1, "deny": 2}


def verdict(call: Call, project: Path) -> tuple[str, str] | None:
    """(deny | ask, reason) or None: the repo's guards.json rules and the role rules (roles.py), strictest first."""
    found = [v for v in (_guards_verdict(call, project),
                         roles.verdict(call.kind, call.paths, call.command, call.shell, call.base, project,
                                       call.agent)) if v]
    return max(found, key=lambda v: STRICTNESS[v[0]]) if found else None


def _guards_verdict(call: Call, project: Path) -> tuple[str, str] | None:
    """(deny | ask, reason) or None for no opinion. Every guards.json from the call's folder up to the filesystem
    root, plus the project's, applies at once and the strictest answer wins: a nested file can add rules, never
    lift the ones above it."""
    if call.kind == "edit":
        for raw in call.paths:
            target = _absolute(raw, call.base)
            for root, guards in _chain(target.parent, project):
                rel = _relative(str(target), root)
                if rel is None:
                    continue
                for g in guards.get("generated", []):
                    if isinstance(g, dict) and isinstance(g.get("glob"), str) and match(rel, g["glob"], CASE_INSENSITIVE_FS):
                        how = g.get("regenerate") or "regenerate it from its source"
                        return "deny", f"{rel} is generated ({g['glob']}); never hand-edit it. {how}."
        return None

    cmd = call.command
    best: tuple[str, str] | None = None
    git_best: tuple[str, str] | None = None
    for _root, guards in _chain(Path(os.path.normpath(call.base)), project):
        for c in guards.get("commands", []):
            if not isinstance(c, dict) or (c.get("tools") and call.shell not in c["tools"]):
                continue
            try:
                if not re.search(c["pattern"], cmd):
                    continue
            except (re.error, TypeError, KeyError):
                continue
            # The guard only ever denies or asks: a rule cannot use it to pre-approve a command.
            decision = c.get("decision", "deny")
            if decision not in ("deny", "ask"):
                decision = "ask"
            if best is None or STRICTNESS[decision] > STRICTNESS[best[0]]:
                best = decision, c.get("reason", "blocked by the repo's guards.json")
            break  # the first matching rule of each file speaks for that file
        git = guards.get("git") or {}
        policy = git.get("writes", "allow")
        if policy in ("ask", "deny") and (git_best is None or STRICTNESS[policy] > STRICTNESS[git_best[0]]):
            git_best = policy, git.get(
                "reason", "git and GitHub writes are the user's call in this repo; run one only when asked for it")
    if git_best and (best is None or STRICTNESS[git_best[0]] > STRICTNESS[best[0]]) \
            and _git_or_gh_write(cmd, call.shell):
        return git_best
    return best


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
    if client == "antigravity":
        # Its plain "ask" is skipped when the user once chose "Always Allow"; the guard's ask must always prompt.
        return json.dumps({"decision": "force_ask" if kind == "ask" else kind, "reason": reason})
    return None


def decide(event: dict, project: Path, client: str | None = None) -> str | None:
    client = client or detect(event)
    call = normalize(event, client, project)
    out = answer(client, event, None) if call is None else answer(client, event, verdict(call, project), call.can_ask)
    if client == "claude-code":  # systemMessage is confirmed for Claude Code only (reference/clients.md)
        warning = _unreadable_warning(event, call.base if call else project, project)
        if warning:
            data = json.loads(out) if out else {}
            data["systemMessage"] = warning
            out = json.dumps(data)
    return out


def check_file(path: Path) -> list[str]:
    """Problems that would make the hook silently ignore a rule (it fails open on them)."""
    duplicates: list[str] = []

    def pairs(items: list[tuple[str, object]]) -> dict:
        seen = set()
        for key, _ in items:
            if key in seen:
                duplicates.append(key)
            seen.add(key)
        return dict(items)

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=pairs)
    except FileNotFoundError:
        return [f"{path}: not found"]
    except ValueError as exc:
        return [f"{path}: invalid JSON ({exc}); the hook ignores the whole file"]
    if not isinstance(data, dict):
        return [f"{path}: the top level must be an object; the hook ignores the whole file"]
    # The hook keeps the last of duplicate keys (rejecting the file would switch every rule off), so the earlier
    # value is silently lost; say so here.
    problems = [f"key {k!r} appears more than once; only the last one counts" for k in dict.fromkeys(duplicates)]
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
    roots = event.get("workspace_roots") or event.get("workspacePaths") or []
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("GEMINI_PROJECT_DIR")
                or (roots[0] if roots else None) or event.get("cwd") or os.getcwd())


def main(args) -> int:
    if getattr(args, "check", False):
        root = Path(args.root or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        problems = check_file(root / GUARDS)
        for p in problems:
            print(f"guards.json: {p}")
        print("guards.json: ok" if not problems else f"guards.json: {len(problems)} problem(s)")
        if os.name == "nt" and not shutil.which("sh"):
            # Claude Code's hook runs `sh "<root>/scripts/stackfoundry.sh" guard`; without Git Bash that fails and,
            # with onFailure "continue", every call goes through. A warning, not a problem in the file.
            print("guard: warning: no `sh` on PATH, so Claude Code's guard hook cannot run here and every call goes "
                  "through. Install Git for Windows (Git Bash).")
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
