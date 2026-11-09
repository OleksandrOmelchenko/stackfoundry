"""Checks shared by every researched file (a technology pack, a domain brief): sources, citations, plain text.

A researched claim is worth keeping only if it names where it came from, so each one cites a key of the file's
`sources` object, and each source has an http(s) url and the date it was read. HTML entities in the text mean the
JSON went through a renderer instead of being written plainly.
"""
from __future__ import annotations

import re

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ENTITY = re.compile(r"&(?:gt|lt|amp|quot|apos|#\d+|#x[0-9a-fA-F]+);")


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
        elif not DATE.match(str(src.get("accessed", ""))):
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
