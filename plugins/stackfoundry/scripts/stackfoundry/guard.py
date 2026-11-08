"""`stackfoundry guard`: the PreToolUse hook. Reads the hook event on stdin and `.claude/stackfoundry/guards.json`.

Decisions:
  - an Edit/Write/MultiEdit/NotebookEdit of a file under a `generated` glob   -> deny, with how to regenerate it;
  - a Bash/PowerShell command matching a `commands` pattern                    -> that entry's decision (deny | ask);
  - a git write (commit, push, reset…) while `git.writes` is "ask" or "deny"   -> ask or deny.
No profile, an unreadable profile, an unexpected event or any internal error -> no opinion (exit 0, no output):
a guard must never wedge a session. Writes nothing.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from .globs import match
from .profile import GUARDS

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}
GIT_WRITE = re.compile(
    r"(?:^|[;&|(\s])git(?:\s+-C\s+\S+)?\s+("
    r"commit|push|merge|rebase|reset|revert|cherry-pick|clean|am|apply|restore|"
    r"tag(?!\s+(?:-l|--list|-n|--contains|--points-at))(?=\s|$)|"
    r"stash\s+(?:drop|pop|clear|push|save)|stash(?=\s*(?:$|[;&|]))|"
    r"branch\s+(?:-[dDmMfc]|--delete|--move|--force)|"
    r"checkout\s+(?:--\s|-f\b|-b\b|-B\b|\.)|switch\s+(?:-[cC]\b|--discard-changes)"
    r")\b"
)
GH_WRITE = re.compile(r"(?:^|[;&|(\s])gh\s+(?:pr\s+(?:create|merge|close|edit|review|comment)|release\s+(?:create|delete|edit)|"
                      r"repo\s+(?:create|delete|edit)|issue\s+(?:create|close|edit|comment))\b")


def decide(event: dict, project: Path) -> dict | None:
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    guards_path = project / GUARDS
    if not guards_path.exists():
        return None
    try:
        guards = json.loads(guards_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    if tool in EDIT_TOOLS:
        raw = tool_input.get("file_path") or tool_input.get("notebook_path")
        rel = _relative(raw, project)
        if rel is None:
            return None
        for g in guards.get("generated", []):
            if match(rel, g["glob"]):
                how = g.get("regenerate") or "regenerate it from its source"
                return _decision("deny", f"{rel} is generated ({g['glob']}); never hand-edit it. {how}.")
        return None

    if tool in SHELL_TOOLS:
        cmd = tool_input.get("command") or ""
        for c in guards.get("commands", []):
            if c.get("tools") and tool not in c["tools"]:
                continue
            try:
                if re.search(c["pattern"], cmd):
                    return _decision(c.get("decision", "deny"), c.get("reason", "blocked by the repo's guards.json"))
            except re.error:
                continue
        policy = (guards.get("git") or {}).get("writes", "allow")
        if policy in ("ask", "deny") and (GIT_WRITE.search(cmd) or GH_WRITE.search(cmd)):
            reason = (guards.get("git") or {}).get(
                "reason", "git and GitHub writes are the user's call in this repo; run one only when asked for it")
            return _decision(policy, reason)
    return None


def _relative(raw: str | None, project: Path) -> str | None:
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        return raw.replace("\\", "/")
    a, b = str(p.resolve()), str(project.resolve())
    if os.name == "nt":
        a_cmp, b_cmp = a.lower(), b.lower()
    else:
        a_cmp, b_cmp = a, b
    if a_cmp == b_cmp or not a_cmp.startswith(b_cmp.rstrip("\\/") + os.sep):
        return None
    return a[len(b.rstrip("\\/")) + 1:].replace("\\", "/")


def _decision(kind: str, reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": kind,
                                   "permissionDecisionReason": f"stackfoundry guard: {reason}"}}


def check_file(path: Path) -> list[str]:
    """Problems that would make the hook silently ignore a rule (it fails open on them)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{path}: not found"]
    except ValueError as exc:
        return [f"{path}: invalid JSON ({exc}); the hook ignores the whole file"]
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
        if any(t not in SHELL_TOOLS for t in c.get("tools", [])):
            problems.append(f"commands[{i}]: tools may only be Bash and PowerShell")
    writes = (data.get("git") or {}).get("writes", "allow")
    if writes not in ("allow", "ask", "deny"):
        problems.append("git.writes must be allow, ask or deny")
    return problems


def main(args) -> int:
    if getattr(args, "check", False):
        root = Path(args.root or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        problems = check_file(root / GUARDS)
        for p in problems:
            print(f"guards.json: {p}")
        print("guards.json: ok" if not problems else f"guards.json: {len(problems)} problem(s)")
        return 1 if problems else 0
    try:
        event = json.loads(sys.stdin.read() or "{}")
        project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd())
        result = decide(event, project)
    except Exception:  # noqa: BLE001 - fail open, never wedge the session
        return 0
    if result:
        print(json.dumps(result))
    return 0
