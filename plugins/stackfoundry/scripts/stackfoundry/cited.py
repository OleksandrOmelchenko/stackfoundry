"""Checks shared by every researched file (a technology pack, a domain brief): sources, citations, plain text.

A researched claim is worth keeping only if it names where it came from, so each one cites a key of the file's
`sources` object, and each source has an http(s) url and the date it was read. HTML entities in the text mean the
JSON went through a renderer instead of being written plainly.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ENTITY = re.compile(r"&(?:gt|lt|amp|quot|apos|#\d+|#x[0-9a-fA-F]+);")
# A public DNS name: dotted labels of letters, digits and hyphens. Placeholders (`api.<host>`), a bare word
# (`internal-host`) or a scheme-like `name:` are not hosts, and become broken WebFetch allow rules when scheduled.
HOST = re.compile(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,62}", re.I)


def url_host(url: str) -> str | None:
    """The host of an http(s) URL when it is a real DNS name, else None."""
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return None
    try:
        host = urlsplit(url).hostname or ""
    except ValueError:
        return None
    return host.lower() if HOST.fullmatch(host) else None


def strings(node, where=""):
    """Every string in a JSON value, with its path (`rules[2].why`)."""
    if isinstance(node, str):
        yield where, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from strings(v, f"{where}.{k}" if where else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from strings(v, f"{where}[{i}]")


def check_sources(doc: dict, errors: list[str]) -> dict:
    """Validate `sources` and return it (an empty dict when it is unusable, after recording the error)."""
    sources = doc.get("sources")
    if not isinstance(sources, dict) or not sources:
        errors.append("sources must be a non-empty object")
        return {}
    for key, src in sources.items():
        if not isinstance(src, dict) or not str(src.get("url", "")).startswith(("http://", "https://")):
            errors.append(f"source [{key}] needs an http(s) url")
        elif url_host(src["url"]) is None:
            errors.append(f"source [{key}]: {src['url']!r} names no real host; re-research it (research-stack)")
        elif not DATE.fullmatch(str(src.get("accessed", ""))):
            errors.append(f"source [{key}] needs an accessed date (YYYY-MM-DD)")
    return sources


def check_cited(items, section: str, sources: dict, errors: list[str], required: tuple[str, ...] = ()) -> None:
    """Each item of a section cites known source keys and carries its required fields."""
    for i, item in enumerate(items or []):
        where = f"{section}[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{where} must be an object")
            continue
        cited = item.get("sources")
        if not cited:
            errors.append(f"{where} cites no source")
        else:
            missing = [k for k in cited if k not in sources]
            if missing:
                errors.append(f"{where} cites unknown source key(s): {', '.join(missing)}")
        for field in required:
            if not item.get(field):
                errors.append(f"{where} needs '{field}'")


def check_plain_text(doc, errors: list[str]) -> None:
    for where, text in strings(doc):
        m = ENTITY.search(text)
        if m:
            errors.append(f"{where}: HTML-escaped text ({m.group(0)}); write plain characters")


# Researched text is rendered inline (a bullet, a table cell, a frontmatter value) into files every later session
# loads. A line break would let fetched text open its own heading or close the frontmatter, and an HTML comment would
# hide text from the person reviewing the rendered file (threat model T9).
CONTROL = re.compile(r"[\x00-\x08\x0a-\x1f\x7f\x85  ]")
COMMENT = re.compile(r"<!--|-->")


def check_inline(doc, errors: list[str]) -> None:
    for where, text in strings(doc):
        m = CONTROL.search(text)
        if m:
            errors.append(f"{where}: a line break or control character ({m.group(0)!r}); researched text is one line")
        if COMMENT.search(text):
            errors.append(f"{where}: an HTML comment marker; it would hide text in the rendered file")
