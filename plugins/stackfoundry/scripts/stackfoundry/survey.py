"""`stackfoundry survey <path>`: read-only inventory of a repository, printed as JSON.

Writes nothing. Detection hints come from reference/detect-signals.json; they are evidence for the surveyor agent,
which confirms them against the code and asks the user about anything ambiguous.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

from . import REFERENCE, gitutil
from .globs import match

MAX_FILES = 200_000
GENERATED_HEAD_BYTES = 2048
COMMENT_START = ("//", "#", "/*", "*", "<!--", "--", '"""', "'''", ";", "'", "%")
GENERATED_MAX_SIZE = 512 * 1024


def load_signals() -> dict:
    return json.loads((REFERENCE / "detect-signals.json").read_text(encoding="utf-8"))


ALWAYS_SKIP_PREFIXES = (".claude/worktrees/", ".git/")


def list_files(root: Path, signals: dict) -> list[str]:
    """Tracked + untracked-but-not-ignored files when `root` is a git work tree (fast, honours .gitignore),
    else a filesystem walk. Either way, skipDirs segments and nested worktrees are left out."""
    skip = set(signals["skipDirs"])
    try:
        # Run from `root`, ls-files lists only files under it, relative to it.
        out = gitutil.run(["ls-files", "--cached", "--others", "--exclude-standard", "-z"], root)
    except gitutil.GitError:
        return walk(root, signals)
    files = []
    for f in out.split("\0"):
        if not f:
            continue
        if f.startswith(ALWAYS_SKIP_PREFIXES) or any(seg in skip for seg in f.split("/")[:-1]):
            continue
        if not (root / f).is_file():  # deleted in the work tree, or a submodule entry
            continue
        files.append(f)
        if len(files) >= MAX_FILES:
            break
    return sorted(files)


def walk(root: Path, signals: dict) -> list[str]:
    skip = set(signals["skipDirs"])
    keep_dot = set(signals["keepDotDirs"])
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in skip and (not d.startswith(".") or d in keep_dot) and not (Path(dirpath) / d).is_symlink()
        )
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        if (rel_dir + "/").startswith(ALWAYS_SKIP_PREFIXES):
            dirnames[:] = []
            continue
        for f in sorted(filenames):
            files.append(f if rel_dir == "." else f"{rel_dir}/{f}")
            if len(files) >= MAX_FILES:
                return files
    return files


def _read(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# --- manifest parsers: each returns (dependency names, extra facts) ---------------------------------------------

def parse_dotnet(text: str) -> tuple[list[str], dict]:
    facts: dict = {}
    sdk = re.search(r"<Project[^>]*\bSdk\s*=\s*\"([^\"]+)\"", text)
    if sdk:
        facts["sdk"] = sdk.group(1).split("/")[0]
    for prop in ("OutputType", "TargetFramework", "TargetFrameworks", "UseWPF", "UseWindowsForms", "UseWinUI",
                 "UseMaui", "IsTestProject", "IsAspireHost", "IsPackable", "Nullable", "LangVersion"):
        m = re.search(rf"<{prop}>\s*([^<]*?)\s*</{prop}>", text)
        if m:
            facts[prop] = m.group(1)
    deps = re.findall(r"<PackageReference\s+[^>]*Include\s*=\s*\"([^\"]+)\"", text)
    refs = re.findall(r"<ProjectReference\s+[^>]*Include\s*=\s*\"([^\"]+)\"", text)
    if refs:
        facts["projectReferences"] = [r.replace("\\", "/") for r in refs]
    return deps, facts


def parse_package_json(text: str) -> tuple[list[str], dict]:
    try:
        data = json.loads(text)
    except ValueError:
        return [], {"error": "invalid JSON"}
    deps: list[str] = []
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        deps += list((data.get(key) or {}).keys())
    facts = {"name": data.get("name"), "scripts": sorted((data.get("scripts") or {}).keys())}
    if data.get("workspaces"):
        facts["workspaces"] = data["workspaces"]
    if data.get("engines"):
        facts["engines"] = data["engines"]
    if data.get("packageManager"):
        facts["packageManager"] = data["packageManager"]
    return deps, facts


_PY_REQ = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def parse_pyproject(text: str) -> tuple[list[str], dict]:
    deps: list[str] = []
    facts: dict = {}
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:  # malformed TOML is reported, not fatal
        return [], {"error": "invalid TOML"}
    project = data.get("project", {})
    facts["name"] = project.get("name")
    for spec in project.get("dependencies", []) or []:
        m = _PY_REQ.match(spec)
        if m:
            deps.append(m.group(1))
    for group in (project.get("optional-dependencies") or {}).values():
        deps += [m.group(1) for s in group if (m := _PY_REQ.match(s))]
    for group in (data.get("dependency-groups") or {}).values():
        deps += [m.group(1) for s in group if isinstance(s, str) and (m := _PY_REQ.match(s))]
    poetry = data.get("tool", {}).get("poetry", {})
    deps += [k for k in (poetry.get("dependencies") or {}) if k != "python"]
    for grp in (poetry.get("group") or {}).values():
        deps += list((grp.get("dependencies") or {}).keys())
    facts["tools"] = sorted((data.get("tool") or {}).keys())
    return [d.lower() for d in deps], facts


def parse_requirements(text: str) -> tuple[list[str], dict]:
    deps = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "[")):
            continue
        m = _PY_REQ.match(line)
        if m:
            deps.append(m.group(1).lower())
    return deps, {}


def parse_go_mod(text: str) -> tuple[list[str], dict]:
    facts = {}
    m = re.search(r"^module\s+(\S+)", text, flags=re.M)
    if m:
        facts["module"] = m.group(1)
    g = re.search(r"^go\s+(\S+)", text, flags=re.M)
    if g:
        facts["go"] = g.group(1)
    deps = re.findall(r"^\s*(?:require\s+)?([a-z0-9.-]+\.[a-z]{2,}/[^\s]+)\s+v", text, flags=re.M)
    return deps, facts


def parse_cargo(text: str) -> tuple[list[str], dict]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return [], {"error": "invalid TOML"}
    deps: list[str] = []
    for key in ("dependencies", "dev-dependencies", "build-dependencies"):
        deps += list((data.get(key) or {}).keys())
    deps += list(((data.get("workspace") or {}).get("dependencies") or {}).keys())
    return deps, {"name": (data.get("package") or {}).get("name")}


def parse_claude_plugin(text: str) -> tuple[list[str], dict]:
    """A Claude Code plugin manifest (.claude-plugin/plugin.json): the plugin itself is the unit."""
    try:
        data = json.loads(text)
    except ValueError:
        return [], {"error": "invalid JSON"}
    deps = [d if isinstance(d, str) else d.get("name", "") for d in data.get("dependencies", []) or []]
    return [d for d in deps if d], {"name": data.get("name"), "version": data.get("version")}


def parse_maven(text: str) -> tuple[list[str], dict]:
    groups = re.findall(r"<groupId>\s*([^<]+?)\s*</groupId>", text)
    artifacts = re.findall(r"<artifactId>\s*([^<]+?)\s*</artifactId>", text)
    return sorted(set(groups + artifacts)), {}


def parse_gradle(text: str) -> tuple[list[str], dict]:
    plugins = re.findall(r"id\s*\(?\s*[\"']([^\"']+)[\"']", text)
    coords = re.findall(r"[\"']([A-Za-z0-9_.-]+):([A-Za-z0-9_.-]+)(?::[^\"']*)?[\"']", text)
    names = plugins + [g for g, _ in coords] + [a for _, a in coords]
    return sorted(set(names)), {}


def parse_gemfile(text: str) -> tuple[list[str], dict]:
    return re.findall(r"^\s*gem\s+[\"']([^\"']+)[\"']", text, flags=re.M), {}


def parse_composer(text: str) -> tuple[list[str], dict]:
    try:
        data = json.loads(text)
    except ValueError:
        return [], {"error": "invalid JSON"}
    return list((data.get("require") or {}).keys()) + list((data.get("require-dev") or {}).keys()), {}


def parse_pubspec(text: str) -> tuple[list[str], dict]:
    deps, section = [], None
    for line in text.splitlines():
        if re.match(r"^(dependencies|dev_dependencies):\s*$", line):
            section = line
            continue
        if re.match(r"^\S", line):
            section = None
        if section:
            m = re.match(r"^\s{2}([A-Za-z0-9_]+):", line)
            if m:
                deps.append(m.group(1))
    return deps, {}


def parse_mix(text: str) -> tuple[list[str], dict]:
    return re.findall(r"\{:([a-z0-9_]+),", text), {}


PARSERS = {
    "dotnet-project": parse_dotnet,
    "npm-package": parse_package_json,
    "python-project": parse_pyproject,
    "python-requirements": parse_requirements,
    "go-module": parse_go_mod,
    "cargo-crate": parse_cargo,
    "maven-project": parse_maven,
    "gradle-project": parse_gradle,
    "ruby-bundle": parse_gemfile,
    "composer-package": parse_composer,
    "dart-package": parse_pubspec,
    "mix-project": parse_mix,
    "swift-package": lambda text: ([], {}),
    "claude-plugin": parse_claude_plugin,
}


# --- hints -----------------------------------------------------------------------------------------------------

def dependency_hints(ecosystem: str, deps: list[str], signals: dict) -> list[dict]:
    rules = signals["dependencies"].get(ecosystem, [])
    lowered = {d.lower() for d in deps}
    hints = []
    for rule in rules:
        name = rule["name"].lower()
        if rule.get("prefix"):
            hit = sorted(d for d in deps if d.lower().startswith(name))
        else:
            hit = [d for d in deps if d.lower() == name]
        if not hit:
            continue
        if any(u.lower() in lowered for u in rule.get("unless", [])):
            continue
        hints.append({"layer": rule["layer"], "tech": rule["tech"], "evidence": f"{ecosystem} dependency {hit[0]}"})
    return hints


def dotnet_hints(facts: dict, signals: dict, is_test: bool = False) -> list[dict]:
    """App-model hints from the SDK and MSBuild properties. A test project's OutputType says how its runner is
    hosted, not what it is, so it gets no console/library fallback."""
    hints = []
    sdk = facts.get("sdk")
    if sdk and sdk in signals["dotnetSdks"]:
        h = signals["dotnetSdks"][sdk]
        hints.append({**h, "evidence": f"Sdk=\"{sdk}\""})
    for rule in signals["dotnetProperties"]:
        if str(facts.get(rule["property"], "")).lower() == rule["value"]:
            hints.append({"layer": rule["layer"], "tech": rule["tech"],
                          "evidence": f"<{rule['property']}>{rule['value']}</{rule['property']}>"})
    has_app_model = any(h["layer"] == "app-model" for h in hints)
    output = str(facts.get("OutputType", "")).lower()
    if is_test or str(facts.get("IsTestProject", "")).lower() == "true":
        return hints
    if not has_app_model and sdk and sdk.startswith("Microsoft.NET.Sdk"):
        if output in ("exe", "winexe"):
            hints.append({"layer": "app-model", "tech": "dotnet-console",
                          "evidence": f"<OutputType>{facts.get('OutputType')}</OutputType> without a UI or web SDK"})
        else:
            hints.append({"layer": "app-model", "tech": "dotnet-library", "evidence": "no OutputType: a class library"})
    return hints


def dedupe(hints: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for h in hints:
        key = (h["layer"], h["tech"])
        if key in seen:
            if h["evidence"] not in seen[key]["evidence"]:
                seen[key]["evidence"].append(h["evidence"])
        else:
            seen[key] = {"layer": h["layer"], "tech": h["tech"], "evidence": [h["evidence"]]}
    order = {"language": 0, "app-model": 1, "capability": 2, "tooling": 3}
    return sorted(seen.values(), key=lambda h: (order.get(h["layer"], 9), h["tech"]))


# --- survey ----------------------------------------------------------------------------------------------------

def survey(root: Path) -> dict:
    root = root.resolve()
    signals = load_signals()
    files = list_files(root, signals)

    languages = Counter()
    ext_map = signals["languagesByExtension"]
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in ext_map:
            languages[ext_map[ext]] += 1

    units: list[dict] = []
    for f in files:
        for m in signals["manifests"]:
            if match(f, m["glob"]):
                deps, facts = PARSERS[m["kind"]](_read(root, f))
                hints = []
                if m.get("language"):
                    hints.append({"layer": "language", "tech": m["language"], "evidence": f"manifest {Path(f).name}"})
                if m.get("appModel"):
                    hints.append({"layer": "app-model", "tech": m["appModel"], "evidence": f"manifest {f}"})
                dep_hints = dependency_hints(m["ecosystem"], deps, signals)
                if m["kind"] == "dotnet-project":
                    is_test = any(h["tech"] == "dotnet-test-project" for h in dep_hints)
                    hints += dotnet_hints(facts, signals, is_test)
                if m["kind"] == "npm-package" and ("typescript" in deps or (root / Path(f).parent / "tsconfig.json").exists()):
                    hints = [{"layer": "language", "tech": "typescript",
                              "evidence": "typescript dependency or tsconfig.json beside package.json"}]
                hints += dep_hints
                unit_dir = Path(f).parent
                if unit_dir.name == ".claude-plugin":  # the plugin is the folder holding .claude-plugin/
                    unit_dir = unit_dir.parent
                unit_path = unit_dir.as_posix() if unit_dir.as_posix() != "." else "."
                units.append({
                    "path": unit_path,
                    "fixture": _is_fixture(unit_path, signals),
                    "manifest": f,
                    "kind": m["kind"],
                    "ecosystem": m["ecosystem"],
                    "facts": {k: v for k, v in facts.items() if v not in (None, [], {})},
                    "dependencies": sorted(set(deps))[:300],
                    "hints": hints,
                })
                break

    repo_hints: list[dict] = []
    for f in files:
        for c in signals["configFiles"]:
            if match(f, c["glob"]):
                hint = {"layer": c["layer"], "tech": c["tech"], "evidence": f"config file {f}"}
                owner = _owning_unit(units, f)
                (owner["hints"] if owner else repo_hints).append(hint)
    # Where the source files live: per unit (nested units excluded), and outside every unit. A product with no
    # manifest (a script folder, a CLI run by a launcher) shows up only here.
    for u in units:
        u["languages"] = Counter()
    loose: Counter = Counter()
    for f in files:
        lang = ext_map.get(os.path.splitext(f)[1].lower())
        if not lang:
            continue
        owner = _owning_unit(units, f)
        if owner:
            owner["languages"][lang] += 1
        else:
            loose[("/".join(f.split("/")[:-1][:3]) or ".", lang)] += 1
    loose_sources = [{"dir": d, "language": lang, "files": n, "fixture": _is_fixture(d, signals)}
                     for (d, lang), n in loose.most_common(40)]
    for u in units:
        u["languages"] = dict(u["languages"].most_common())
        u["hints"] = dedupe(u["hints"])
        u["isTestProject"] = any(h["tech"] in ("dotnet-test-project",) for h in u["hints"]) or bool(
            re.search(r"(^|[./_-])(tests?|specs?)([./_-]|$)", u["path"], flags=re.I)
        )

    # Fixture folders are reported once, as roots; their contents stay out of the repo-wide counts below.
    fixture_roots = sorted({_fixture_root(f, signals) for f in files if _is_fixture(f, signals)})
    product_files = [f for f in files if not _is_fixture(f, signals)]

    infrastructure: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for f in product_files:
        for i in signals["infrastructure"]:
            if match(f, i["glob"]):
                infrastructure[i["category"]][i["tech"]].append(f)

    test_dirs = Counter()
    test_files = 0
    for f in product_files:
        parts = f.split("/")
        for depth, part in enumerate(parts[:-1]):
            if part.lower() in signals["testDirNames"]:
                test_dirs["/".join(parts[: depth + 1])] += 1
                break
        if any(match(f, g) for g in signals["testFileGlobs"]):
            test_files += 1

    generated = Counter()
    exts = set(signals["generatedScanExtensions"])
    markers = signals["generatedMarkers"]
    for f in product_files:
        if os.path.splitext(f)[1].lower() not in exts:
            continue
        p = root / f
        try:
            if p.stat().st_size > GENERATED_MAX_SIZE:
                continue
            with p.open("rb") as fh:
                head = fh.read(GENERATED_HEAD_BYTES).decode("utf-8", errors="replace")
        except OSError:
            continue
        if any(mk in line for line in _leading_comment(head) for mk in markers):
            generated[Path(f).parent.as_posix()] += 1

    solution = [f for f in files if any(match(f, g) for g in signals["solutionFiles"])]

    claude = _claude_inventory(root, files)
    docs = sorted({f.split("/")[1] for f in files if f.startswith("docs/") and f.count("/") >= 2})

    git: dict = {}
    try:
        git["defaultBranch"] = gitutil.default_branch(root)
        remote = gitutil.run(["remote", "get-url", "origin"], root).strip()
        git["remoteHost"] = re.sub(r"^(?:https?://|git@)([^/:]+).*$", r"\1", remote)
    except gitutil.GitError:
        pass

    return {
        "schemaVersion": 1,
        "root": root.as_posix(),
        "fileCount": len(files),
        "truncated": len(files) >= MAX_FILES,
        "languages": dict(languages.most_common()),
        "units": units,
        "looseSources": loose_sources,
        "repoHints": dedupe(repo_hints),
        "solutionFiles": solution,
        "infrastructure": {k: dict(v) for k, v in infrastructure.items()},
        "tests": {"dirs": dict(test_dirs.most_common(40)), "fileCount": test_files},
        "generatedDirs": dict(generated.most_common(50)),
        "fixtureRoots": fixture_roots,
        "docs": {"root": "docs" if any(f.startswith("docs/") for f in files) else None, "sections": docs},
        "claude": claude,
        "git": git,
    }


def _leading_comment(head: str) -> list[str]:
    """The file's header: lines up to the first line of code. A generator stamps its marker there; the same words
    further down are usually a string in code (a test, a linter rule), not a sign the file is generated."""
    lines = []
    for line in head.splitlines():
        s = line.strip()
        if s and not s.startswith(COMMENT_START):
            break
        lines.append(s)
    return lines


def _is_fixture(path: str, signals: dict) -> bool:
    """Under a folder of test fixtures or samples: evidence that it is test data, not a product to target."""
    names = {n.lower() for n in signals.get("fixtureDirNames", [])}
    return any(seg.lower() in names for seg in path.split("/"))


def _fixture_root(path: str, signals: dict) -> str:
    names = {n.lower() for n in signals.get("fixtureDirNames", [])}
    parts = path.split("/")
    i = next(i for i, seg in enumerate(parts) if seg.lower() in names)
    return "/".join(parts[: i + 1])


def _owning_unit(units: list[dict], f: str) -> dict | None:
    best = None
    for u in units:
        base = u["path"]
        if base == "." or f == base or f.startswith(base + "/"):
            if best is None or len(base) > len(best["path"]) or best["path"] == ".":
                best = u
    return best


def _claude_inventory(root: Path, files: list[str]) -> dict:
    inv = {
        "claudeMd": [f for f in files if Path(f).name == "CLAUDE.md"],
        "skills": sorted({f.split("/")[2] for f in files if f.startswith(".claude/skills/") and f.endswith("/SKILL.md")}),
        "agents": sorted(Path(f).stem for f in files if f.startswith(".claude/agents/") and f.endswith(".md")),
        "rules": sorted(Path(f).stem for f in files if f.startswith(".claude/rules/") and f.endswith(".md")),
        "hasSettings": (root / ".claude" / "settings.json").exists(),
        "hasStackfoundryProfile": (root / ".stackfoundry" / "targets.json").exists(),
        "hasLegacyStackfoundryProfile": (root / ".claude" / "stackfoundry" / "targets.json").exists(),
    }
    settings = root / ".claude" / "settings.json"
    if settings.exists():
        try:
            data = json.loads(settings.read_text(encoding="utf-8-sig"))
            inv["settingsHooks"] = sorted((data.get("hooks") or {}).keys())
            inv["enabledPlugins"] = data.get("enabledPlugins")
        except ValueError:
            inv["settingsError"] = "invalid JSON"
    return inv


def main(args) -> int:
    root = Path(args.path)
    if not root.is_dir():
        print(f"survey: {root} is not a directory", file=sys.stderr)
        return 2
    print(json.dumps(survey(root), indent=2 if args.pretty else None, ensure_ascii=False))
    return 0
