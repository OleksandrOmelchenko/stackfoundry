"""Read-only git helpers. Nothing here writes to the repository."""
from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


def run(args: list[str], cwd: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except FileNotFoundError as exc:  # git not installed
        raise GitError("git is not on PATH") from exc
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout


def repo_root(start: Path) -> Path:
    return Path(run(["rev-parse", "--show-toplevel"], start).strip())


def changed_files(root: Path, base: str | None = None) -> list[str]:
    """Files changed against `base` (merge-base form, `base...HEAD`), or the uncommitted tree plus untracked files."""
    if base:
        out = run(["diff", "--name-only", f"{base}...HEAD"], root)
        files = out.splitlines()
        # A branch review also covers what is still uncommitted on top of it.
        files += run(["diff", "--name-only", "HEAD"], root).splitlines()
    else:
        try:
            files = run(["diff", "--name-only", "HEAD"], root).splitlines()
        except GitError:  # no commit yet
            files = run(["diff", "--name-only", "--cached"], root).splitlines()
    files += run(["ls-files", "--others", "--exclude-standard"], root).splitlines()
    seen: dict[str, None] = {}
    for f in files:
        f = f.strip()
        if f:
            seen.setdefault(f.replace("\\", "/"), None)
    return list(seen)


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
    return [f for f in run(["ls-files"], root).splitlines() if f]
