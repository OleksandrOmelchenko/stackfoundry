"""Atomic file writes that keep a file's permissions.

`tempfile.mkstemp` creates its file with mode 0600, and `os.replace` carries that mode onto the target, so a spliced
`AGENTS.md` that was 0644 came back readable by its owner only. `atomic_write` gives the temp file the target's
current mode, or the mode a plain `open()` would give a new file under the current umask, before the replace.
"""
from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path


def _umask() -> int:
    current = os.umask(0)  # the only portable way to read it is to set it and put it back
    os.umask(current)
    return current


def _mode_for(path: Path) -> int:
    try:
        return stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        return 0o666 & ~_umask()


def atomic_write(path: Path, text: str, newline: str = "\n") -> None:
    """Write `text` to `path` with `newline` line endings, so an interrupted write never leaves a truncated file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = _mode_for(path)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as fh:
            fh.write(text)
        if os.name != "nt":  # Windows has no POSIX mode bits; chmod there only toggles read-only
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
