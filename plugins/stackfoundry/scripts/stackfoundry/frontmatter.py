"""A minimal YAML-frontmatter reader for skill, agent and rulebook files.

Supports what those files use: `key: value`, quoted strings, inline lists (`[a, b]`), block lists (`- item`),
booleans and numbers. Anything richer is returned as the raw string; the caller decides whether that is an error.
"""
from __future__ import annotations

import re

_FENCE = "---"


def split(text: str) -> tuple[dict, str, list[str]]:
    """Return (fields, body, errors). A file without frontmatter yields ({}, text, [])."""
    text = text.lstrip("﻿")
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FENCE:
        return {}, text, []
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == _FENCE)
    except StopIteration:
        return {}, text, ["frontmatter opens with '---' but never closes"]
    fields, errors = parse(lines[1:end])
    body = "\n".join(lines[end + 1:])
    return fields, body, errors


def parse(lines: list[str]) -> tuple[dict, list[str]]:
    fields: dict = {}
    errors: list[str] = []
    key = None
    for n, raw in enumerate(lines, start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s+(.*)$", raw) or re.match(r"^-\s+(.*)$", raw)
        if item and key is not None:
            if not isinstance(fields.get(key), list):
                fields[key] = []
            fields[key].append(_scalar(item.group(1)))
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+):\s*(.*)$", raw)
        if not m:
            if key is not None and raw.startswith((" ", "\t")) and isinstance(fields.get(key), str):
                fields[key] = (fields[key] + " " + raw.strip()).strip()
                continue
            errors.append(f"line {n}: cannot parse {raw.strip()!r}")
            continue
        key, value = m.group(1), m.group(2).strip()
        if key in fields:
            errors.append(f"line {n}: duplicate key {key!r}")
        if value == "" or value in ("|", ">", "|-", ">-"):
            fields[key] = ""
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            fields[key] = [_scalar(v) for v in _split_list(inner)] if inner else []
        else:
            fields[key] = _scalar(value)
    return fields, errors


def _split_list(inner: str) -> list[str]:
    out, buf, quote = [], "", None
    for ch in inner:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == ",":
            out.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(buf.strip())
    return out


def _scalar(value: str):
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        inner = v[1:-1]
        return inner.replace('\\"', '"') if v[0] == '"' else inner.replace("''", "'")
    low = v.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v
