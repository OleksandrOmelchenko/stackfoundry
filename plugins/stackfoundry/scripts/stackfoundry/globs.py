"""Path globs as the profile writes them: forward slashes, `**` spans directories, `*` and `?` stay within one.

`src/api/**` matches everything under `src/api/`; `**/*.cs` matches a `.cs` file at any depth, the top level
included; a pattern without a slash (`*.md`) matches the file name at any depth, as in .gitignore.
"""
from __future__ import annotations

import re
from functools import lru_cache


def normalize(path: str) -> str:
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


@lru_cache(maxsize=1024)
def compile_glob(pattern: str) -> re.Pattern[str]:
    pat = normalize(pattern)
    if "/" not in pat.rstrip("/"):
        pat = "**/" + pat
    if pat.endswith("/"):
        pat += "**"
    out = []
    i = 0
    while i < len(pat):
        c = pat[i]
        if pat.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pat.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "[":
            j = pat.find("]", i + 1)
            if j == -1:
                out.append(re.escape(c))
                i += 1
            else:
                body = pat[i + 1:j]
                if body.startswith("!"):
                    body = "^" + body[1:]
                out.append("[" + body.replace("\\", "\\\\") + "]")
                i = j + 1
        elif c == "{":
            j = pat.find("}", i + 1)
            if j == -1:
                out.append(re.escape(c))
                i += 1
            else:
                alts = pat[i + 1:j].split(",")
                out.append("(?:" + "|".join(re.escape(a) for a in alts) + ")")
                i = j + 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def match(path: str, pattern: str) -> bool:
    return compile_glob(pattern).match(normalize(path)) is not None


def match_any(path: str, patterns: list[str] | tuple[str, ...]) -> bool:
    return any(match(path, p) for p in patterns or ())
