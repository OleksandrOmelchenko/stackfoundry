"""`stackfoundry product check|status`: the product profile and its researched domain brief. Read-only.

check   Validate `.stackfoundry/product.json` (schema reference/schemas/product.schema.json) or a domain brief
        (`.stackfoundry/domain/<domainId>.json`, reference/schemas/domain.schema.json): required fields, enums, every
        researched item citing a known source, plain text. Errors exit 1.
status  JSON for whats-next and schedule: does the product profile exist and pass, which domain brief it points to,
        how old the brief is against `researchRefreshDays`, and whether the product's scope moved since the research.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from . import config
from .cited import DATE, check_cited, check_inline, check_plain_text, check_sources
from .profile import PROFILE_DIR, find_root

PRODUCT = PROFILE_DIR / "product.json"
DOMAIN_DIR = PROFILE_DIR / "domain"
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
STAGES = ("idea", "mvp", "growth", "mature", "maintenance")
TIERS = ("table-stakes", "expected", "differentiator")
MATURITY = ("emerging", "growing", "mainstream", "declining")
PRODUCT_KEYS = {"schemaVersion", "name", "summary", "category", "domainId", "audiences", "channels", "markets",
                "monetization", "stage", "goals", "nonGoals", "evidence"}


def _str_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)


def check_product(data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if data.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    for key in ("name", "summary", "category"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"'{key}' is required")
    if not KEBAB.fullmatch(str(data.get("domainId", ""))):
        errors.append("'domainId' must be a kebab-case id (the domain brief's file name)")
    if not _str_list(data.get("audiences")) or not data.get("audiences"):
        errors.append("'audiences' must be a non-empty list of strings")
    for key in ("channels", "markets", "goals", "nonGoals"):
        if key in data and not _str_list(data[key]):
            errors.append(f"'{key}' must be a list of strings")
    if data.get("stage") not in STAGES:
        errors.append(f"'stage' must be one of {', '.join(STAGES)}")
    for i, ev in enumerate(data.get("evidence", []) or []):
        if not isinstance(ev, dict) or not ev.get("claim") or not ev.get("where"):
            errors.append(f"evidence[{i}] needs 'claim' and 'where'")
    for key in sorted(set(data) - PRODUCT_KEYS):
        errors.append(f"unknown key {key!r}")
    if not data.get("markets"):
        warnings.append("no 'markets': the domain research cannot tell which regulations apply")
    if not data.get("evidence"):
        warnings.append("no 'evidence': nothing in the repo backs the category")
    check_plain_text(data, errors)
    check_inline(data, errors)
    return errors, warnings


def check_domain(data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if data.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if not KEBAB.fullmatch(str(data.get("id", ""))):
        errors.append("'id' must be a kebab-case id (product.json's domainId)")
    if not data.get("title"):
        errors.append("'title' is required")
    if not DATE.fullmatch(str(data.get("researchedAt", ""))):
        errors.append("researchedAt must be a YYYY-MM-DD date")
    if not isinstance(data.get("scope"), dict):
        errors.append("'scope' must be an object (the product facts the research covered)")
    sources = check_sources(data, errors)
    if not data.get("capabilities"):
        errors.append("capabilities must be a non-empty list")
    check_cited(data.get("capabilities"), "capabilities", sources, errors, ("id", "name", "tier", "why", "signals"))
    check_cited(data.get("regulations"), "regulations", sources, errors, ("name", "appliesWhen", "obligations"))
    check_cited(data.get("metrics"), "metrics", sources, errors, ("name", "why"))
    check_cited(data.get("weaknesses"), "weaknesses", sources, errors, ("name", "failure", "lookFor"))
    check_cited(data.get("trends"), "trends", sources, errors, ("name", "what", "maturity"))
    ids: set[str] = set()
    for i, cap in enumerate(data.get("capabilities", []) or []):
        if not isinstance(cap, dict):
            continue
        if cap.get("tier") and cap["tier"] not in TIERS:
            errors.append(f"capabilities[{i}].tier must be one of {', '.join(TIERS)}")
        if cap.get("id") in ids:
            errors.append(f"capabilities[{i}]: duplicate id {cap['id']!r}")
        ids.add(cap.get("id"))
        if "signals" in cap and not _str_list(cap["signals"]):
            errors.append(f"capabilities[{i}].signals must be a list of strings")
    for i, trend in enumerate(data.get("trends", []) or []):
        if isinstance(trend, dict) and trend.get("maturity") and trend["maturity"] not in MATURITY:
            errors.append(f"trends[{i}].maturity must be one of {', '.join(MATURITY)}")
    if not any(isinstance(c, dict) and c.get("tier") == "table-stakes" for c in data.get("capabilities", []) or []):
        warnings.append("no table-stakes capability: the brief cannot say what the product must have")
    for section in ("regulations", "weaknesses"):
        if not data.get(section):
            warnings.append(f"no {section} section")
    check_plain_text(data, errors)
    check_inline(data, errors)
    return errors, warnings


def _load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: the top level must be an object")
    return data


def status(root: Path) -> dict:
    out: dict = {"product": PRODUCT.as_posix(), "productExists": (root / PRODUCT).is_file()}
    if not out["productExists"]:
        return out
    product = _load(root / PRODUCT)
    errors, _ = check_product(product)
    out["productErrors"] = errors
    domain_id = product.get("domainId", "")
    brief = (DOMAIN_DIR / f"{domain_id}.json").as_posix()
    out.update({"domainId": domain_id, "brief": brief, "briefExists": (root / brief).is_file()})
    if not out["briefExists"]:
        out["needsResearch"] = "missing"
        return out
    data = _load(root / brief)
    errors, _ = check_domain(data)
    out["briefErrors"] = errors
    refresh = int(config.load(root).get("researchRefreshDays", 90))
    try:
        age = (date.today() - date.fromisoformat(str(data.get("researchedAt")))).days
    except ValueError:
        age = None
    scope = data.get("scope") or {}
    moved = [k for k in ("category", "audiences", "markets") if k in product and scope.get(k) != product.get(k)]
    out.update({"researchedAt": data.get("researchedAt"), "ageDays": age, "refreshDays": refresh,
                "scopeMoved": moved})
    out["needsResearch"] = ("invalid" if errors else "stale" if age is None or age > refresh
                            else "scope moved" if moved else None)
    return out


def main(args) -> int:
    if args.action == "status":
        root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
        print(json.dumps(status(root), indent=2, ensure_ascii=False))
        return 0
    if not args.file:
        raise ValueError("check needs a file: .stackfoundry/product.json or .stackfoundry/domain/<id>.json")
    path = Path(args.file)
    data = _load(path)
    is_domain = "capabilities" in data or path.parent.name == DOMAIN_DIR.name
    errors, warnings = (check_domain if is_domain else check_product)(data)
    for e in errors:
        print(f"error: {e}")
    for w in warnings:
        print(f"warning: {w}")
    kind = "domain brief" if is_domain else "product"
    print(f"{kind} {data.get('id') or data.get('name') or path.name}: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0
