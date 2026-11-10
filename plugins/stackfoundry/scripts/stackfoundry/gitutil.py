"""Read-only git helpers. Nothing here writes to the repository."""
from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path


class GitError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def git_exe() -> str:
    """git's absolute path, from absolute PATH entries only. A bare "git" on Windows can resolve to a git.exe in the
    current directory, which here is the user's repo: a file planted there must never run."""
    # On Windows only git.exe: a git.bat or git.cmd would run through cmd.exe, which re-parses the arguments.
    exts = [".exe"] if os.name == "nt" else [""]
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d or not os.path.isabs(d):
            continue
        for ext in exts:
            candidate = os.path.join(d, "git" + ext)
            if os.path.isfile(candidate) and (os.name == "nt" or os.access(candidate, os.X_OK)):
                return candidate
    raise GitError("git is not on PATH")


def check_ref(value: str) -> str:
    """A revision or range from the command line. One starting with '-' would reach git as an option
    (`--output=<file>` turns a read-only diff into a write), so it is refused."""
    if not value or value.startswith("-"):
        raise GitError(f"not a revision or range: {value!r}")
    return value


def run(args: list[str], cwd: Path, timeout: int = 120) -> str:
    try:
        proc = subprocess.run(
            [git_exe(), *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError as exc:  # git not installed
        raise GitError("git is not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"git {' '.join(args)} did not finish within {timeout}s") from exc
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout


def repo_root(start: Path) -> Path:
    return Path(run(["rev-parse", "--show-toplevel"], start).strip())


def paths(args: list[str], root: Path) -> list[str]:
    """A git command that lists paths, run with -z: without it git quotes and escapes non-ASCII names
    ("\\320\\220…"), which then match no glob and silently drop out of change sets."""
    return [p.replace("\\", "/") for p in run([*args, "-z"], root).split("\0") if p]


def changed_files(root: Path, base: str | None = None) -> list[str]:
    """Files changed against `base` (merge-base form, `base...HEAD`), or the uncommitted tree plus untracked files."""
    if base:
        files = paths(["diff", "--name-only", f"{check_ref(base)}...HEAD"], root)
        # A branch review also covers what is still uncommitted on top of it.
        files += paths(["diff", "--name-only", "HEAD"], root)
    else:
        try:
            files = paths(["diff", "--name-only", "HEAD"], root)
        except GitError:  # no commit yet
            files = paths(["diff", "--name-only", "--cached"], root)
    files += paths(["ls-files", "--others", "--exclude-standard"], root)
    return list(dict.fromkeys(files))


def default_branch(root: Path) -> str | None:
    try:
        ref = run(["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"], root).strip()
        return ref.rsplit("/", 1)[-1] or None
    except GitError:
        try:
            return run(["rev-parse", "--abbrev-ref", "HEAD"], root).strip() or None
        except GitError:
            return None


def tracked_files(root: Path) -> list[str]:
    return paths(["ls-files"], root)
