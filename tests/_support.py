"""Shared helpers for the unittest suite: import path, temp repos, running the CLI as a hook would."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "stackfoundry"
SCRIPTS = PLUGIN / "scripts"
CLI = SCRIPTS / "stackfoundry" / "cli.py"
LAUNCHER = PLUGIN / "bin" / "stackfoundry"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

HAS_GIT = shutil.which("git") is not None


class TempRepo:
    """A temporary directory, optionally a git repo with one commit. Use as a context manager."""

    def __init__(self, files: dict[str, str] | None = None, git: bool = False):
        self.files = files or {}
        self.git = git

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        write(self.path, self.files)
        if self.git:
            git(self.path, "init", "-q", "-b", "main")
            git(self.path, "add", "-A")
            git(self.path, "commit", "-q", "-m", "init", "--allow-empty")
        return self.path

    def __exit__(self, *exc):
        self._tmp.cleanup()


def write(root: Path, files: dict[str, str]):
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def git(root: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *args], cwd=root,
                          check=True, capture_output=True, text=True, encoding="utf-8", env=env).stdout


def run_cli(args: list[str], cwd: Path | None = None, stdin: str = "", env: dict | None = None):
    return subprocess.run([sys.executable, "-I", str(CLI), *args], cwd=cwd, input=stdin, capture_output=True,
                          text=True, encoding="utf-8", env={**os.environ, **(env or {})})


def targets_json(root: Path, data: dict):
    write(root, {".claude/stackfoundry/targets.json": json.dumps(data)})
