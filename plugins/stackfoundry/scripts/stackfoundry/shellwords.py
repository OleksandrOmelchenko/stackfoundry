"""Reading a shell command the way the guard needs: split into simple commands, each as argv, and judged.

Covers POSIX shells and PowerShell well enough for the forms an agent writes on its own: separators (`;`, `&&`,
`||`, `|`, `&`, newlines), subshells and command substitution, `sh -c '…'` / `pwsh -Command …` / `cmd /c …`,
environment prefixes and wrappers (`env`, `sudo`, `nohup`…), path-prefixed programs (`/usr/bin/git`, `git.exe`).
It is a guardrail against accidents, not a security boundary: a command written to hide itself can.
"""
from __future__ import annotations

import re
import shlex

SEPARATORS = set(";&|()")
WRAPPERS = {"env", "command", "builtin", "exec", "nohup", "time", "sudo", "nice", "stdbuf", "timeout"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
POWERSHELLS = {"pwsh", "powershell"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_DEPTH = 4


def _tokens(cmd: str, shell: str) -> list[str] | None:
    lexer = shlex.shlex(cmd.replace("`", " ; ").replace("\r", " ").replace("\n", " ; "),
                        posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    if shell == "PowerShell":
        lexer.escape = ""  # a backslash separates path parts there (C:\x\git.exe); it escapes nothing
    try:
        return list(lexer)
    except ValueError:  # unbalanced quotes
        return None


def program(token: str) -> str:
    """`/usr/bin/git`, `C:\\Program Files\\Git\\bin\\git.exe` and `git` are all `git`."""
    name = re.split(r"[\\/]", token)[-1].lower()
    return re.sub(r"\.(exe|cmd|bat|com)$", "", name)


def segments(cmd: str, shell: str = "Bash", depth: int = 0) -> list[list[str]] | None:
    """Each simple command as argv (wrappers and VAR=x prefixes removed, `sh -c` scripts expanded), or None when
    the command cannot be split (unbalanced quotes): the caller falls back to whole-string patterns.
    `shell` is Bash or PowerShell: how backslashes read."""
    tokens = _tokens(cmd, shell)
    if tokens is None:
        return None
    out: list[list[str]] = []
    current: list[str] = []
    for tok in [*tokens, ";"]:
        if tok and set(tok) <= SEPARATORS:
            if current:
                out += _expand(current, shell, depth)
            current = []
        else:
            current.append(tok)
    return out


def _expand(argv: list[str], shell: str, depth: int) -> list[list[str]]:
    argv = [a for a in argv if a != "$"]  # the `$` of `$(…)` is left behind by the split
    while argv and (ASSIGNMENT.match(argv[0]) or program(argv[0]) in WRAPPERS):
        head = program(argv[0])
        argv = argv[1:]
        if head == "timeout" and argv and not argv[0].startswith("-"):
            argv = argv[1:]  # the duration
        while head in ("env", "sudo", "nice", "stdbuf", "timeout") and argv and argv[0].startswith("-"):
            argv = argv[1:]
    if not argv:
        return []
    prog = program(argv[0])
    script, inner = None, shell
    if prog in SHELLS:
        inner = "Bash"
        for i, a in enumerate(argv[1:], start=1):
            if a.startswith("-") and not a.startswith("--") and "c" in a[1:] and i + 1 < len(argv):
                script = argv[i + 1]
                break
    elif prog in POWERSHELLS:
        inner = "PowerShell"
        for i, a in enumerate(argv[1:], start=1):
            if a.lower() in ("-c", "-command", "-com", "-comm") and i + 1 < len(argv):
                script = " ".join(argv[i + 1:])
                break
    elif prog == "cmd":
        for i, a in enumerate(argv[1:], start=1):
            if a.lower() in ("/c", "/k", "/s/c") and i + 1 < len(argv):
                script = " ".join(argv[i + 1:])
                break
    elif prog == "eval" and len(argv) > 1:
        script = " ".join(argv[1:])
    if script is not None and depth < _DEPTH:
        parts = segments(script, inner, depth + 1)
        return parts if parts is not None else [argv]
    return [argv]


def _positionals(args: list[str], takes_value: set[str] = frozenset()) -> list[str]:
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a.startswith("-"):
            skip = a in takes_value
            continue
        out.append(a)
    return out


def _short_flags(args: list[str]) -> set[str]:
    """The letters of every single-dash flag (`-fd` gives f and d)."""
    return {c for a in args if a.startswith("-") and not a.startswith("--") for c in a[1:]}


GIT_GLOBAL_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env",
                    "--exec-path", "--attr-source"}
GIT_ALWAYS = {"commit", "push", "pull", "merge", "rebase", "reset", "revert", "cherry-pick", "am", "restore", "mv",
              "rm", "update-ref", "filter-branch", "filter-repo", "replace", "prune", "update-index", "read-tree",
              "commit-tree", "bisect"}
GIT_SUB = {"notes": {"add", "append", "copy", "edit", "merge", "prune", "remove"},
           "worktree": {"add", "remove", "move", "prune", "repair", "lock", "unlock"},
           "remote": {"add", "remove", "rm", "rename", "set-url", "set-head", "set-branches", "prune", "update"},
           "submodule": {"add", "update", "deinit", "sync", "init", "set-branch", "set-url", "absorbgitdirs",
                         "foreach"},
           "reflog": {"expire", "delete"}}


def git_write(argv: list[str]) -> bool:
    """Whether a `git …` argv changes the repository, its refs, its working tree or its config."""
    if not argv or program(argv[0]) != "git":
        return False
    i = 1
    while i < len(argv) and argv[i].startswith("-"):
        i += 2 if (argv[i] in GIT_GLOBAL_VALUE and "=" not in argv[i]) else 1
    if i >= len(argv):
        return False
    verb, args = argv[i], argv[i + 1:]
    pos = _positionals(args)
    if verb in GIT_ALWAYS:
        return not (verb == "bisect" and pos[:1] in (["log"], ["view"], ["visualize"]))
    if verb in GIT_SUB:
        first = _positionals(args, {"--ref"})
        return bool(first) and first[0] in GIT_SUB[verb]
    if verb == "clean":
        return not ({"n"} & _short_flags(args) or "--dry-run" in args)
    if verb == "apply":
        return "--index" in args or "--cached" in args or not (
            {"--check", "--stat", "--numstat", "--summary"} & set(args))
    if verb == "symbolic-ref":
        return len(pos) >= 2 or "-d" in args or "--delete" in args
    if verb == "tag":
        reads = {"-l", "--list", "--contains", "--no-contains", "--points-at", "--merged", "--no-merged", "-v",
                 "--verify"}
        if not args or reads & set(args) or any(a.startswith("-n") for a in args):
            return False
        return True
    if verb == "stash":
        return not (pos[:1] in (["list"], ["show"], ["create"]))
    if verb == "branch":
        long_writes = {"--delete", "--move", "--copy", "--force", "--set-upstream-to", "--unset-upstream",
                       "--edit-description", "--track", "--no-track", "--create-reflog"}
        if long_writes & {a.split("=")[0] for a in args} or set("dDmMcCfu") & _short_flags(args):
            return True
        reads = {"-l", "--list", "--contains", "--no-contains", "--merged", "--no-merged", "--points-at",
                 "--show-current", "--format", "--sort"}
        if reads & {a.split("=")[0] for a in args} or {"a", "r", "v", "l"} & _short_flags(args):
            return False
        return bool(_positionals(args, {"--format", "--sort", "--color", "--column"}))
    if verb == "checkout":
        return bool({"--", "-f", "--force", "-b", "-B", "--orphan", ".", "--ours", "--theirs", "-p",
                     "--patch"} & set(args))
    if verb == "switch":
        return bool({"-c", "-C", "--create", "--force-create", "--discard-changes", "-f", "--force",
                     "--orphan"} & set(args))
    if verb == "config":
        flags = {a.split("=")[0] for a in args}
        if flags & {"--unset", "--unset-all", "--add", "--replace-all", "--rename-section", "--remove-section",
                    "--edit", "-e"}:
            return True
        if flags & {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--list", "-l", "--get-color",
                    "--get-colorbool"}:
            return False
        names = _positionals(args, {"-f", "--file", "--blob", "--type", "-t", "--default", "--comment", "--value"})
        if names[:1] in (["set"], ["unset"], ["rename-section"], ["remove-section"], ["edit"]):
            return True
        if names[:1] in (["get"], ["list"]):
            return False
        return len(names) >= 2
    return False


GH_WRITES = {
    "pr": {"create", "merge", "close", "reopen", "edit", "review", "comment", "ready", "lock", "unlock"},
    "issue": {"create", "close", "reopen", "edit", "comment", "delete", "transfer", "lock", "unlock", "pin",
              "unpin", "develop"},
    "release": {"create", "delete", "edit", "upload", "delete-asset"},
    "repo": {"create", "delete", "edit", "fork", "rename", "archive", "unarchive", "sync", "deploy-key"},
    "workflow": {"run", "enable", "disable"},
    "run": {"rerun", "cancel", "delete"},
    "label": {"create", "edit", "delete", "clone"},
    "secret": {"set", "delete", "remove"},
    "variable": {"set", "delete"},
    "gist": {"create", "edit", "delete", "rename"},
    "cache": {"delete"},
    "project": {"create", "edit", "delete", "close", "copy", "link", "unlink", "item-add", "item-archive",
                "item-create", "item-delete", "item-edit", "field-create", "field-delete", "mark-template"},
}
GH_VALUE = {"-R", "--repo"}
GH_FIELDS = ("-f", "-F", "--field", "--raw-field", "--input")


def gh_write(argv: list[str]) -> bool:
    """Whether a `gh …` argv writes to GitHub."""
    if not argv or program(argv[0]) != "gh":
        return False
    args = argv[1:]
    pos = _positionals(args, GH_VALUE)
    if not pos:
        return False
    if pos[0] == "api":
        method = None
        for i, a in enumerate(args):
            if a in ("-X", "--method") and i + 1 < len(args):
                method = args[i + 1]
            elif a.startswith("--method="):
                method = a.split("=", 1)[1]
            elif a.startswith("-X") and len(a) > 2:
                method = a[2:]
        if method is not None:
            return method.upper() != "GET"
        if "graphql" in pos[1:2]:
            return any("mutation" in a for a in args)
        return any(a in GH_FIELDS or a.startswith(GH_FIELDS[:2]) and len(a) > 2 or a.startswith(
            ("--field=", "--raw-field=", "--input=")) for a in args)
    return len(pos) > 1 and pos[1] in GH_WRITES.get(pos[0], set())
