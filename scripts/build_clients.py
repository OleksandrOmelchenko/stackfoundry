"""Generate every assistant's plugin files from the Claude Code source layout.

The source of truth is the plugin as Claude Code reads it: `.claude-plugin/plugin.json`, `skills/`, `agents/*.md`,
`hooks/hooks.json`. This script writes, for the other assistants (plugins/stackfoundry/reference/clients.md):

- `plugin.json` at the plugin root: the Agent Plugins 1.0 manifest Codex, Copilot and Cursor read, with the Codex
  overlay under `extensions.com.openai`;
- `com.openai/hooks.json`: the guard hook in Codex's format;
- `com.github.copilot/agents/*.agent.md` and `com.github.copilot/hooks/hooks.json`: Copilot's agents (tool grants
  mapped to its aliases) and the guard hook in its format;
- `.cursor-plugin/plugin.json` and `com.cursor/hooks.json`: Cursor's manifest and guard hooks;
- the marketplace catalogs at the repository root: `.agents/plugins/marketplace.json` (Codex),
  `.github/plugin/marketplace.json` (Copilot) and `.cursor-plugin/marketplace.json` (Cursor);
- with `--gemini-out <dir>` only: a complete Gemini CLI extension (not committed; the release workflow attaches it).

Usage (from the repository root):
    python scripts/build_clients.py            write the committed files
    python scripts/build_clients.py --check    exit 1 and list every file that differs (pre-commit and CI)
    python scripts/build_clients.py --gemini-out <dir>
Standard library only. Deterministic: the same source always gives the same bytes.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "stackfoundry"
sys.path.insert(0, str(PLUGIN / "scripts"))

from stackfoundry.clients import render_agent  # noqa: E402

AGENT_PLUGINS_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
AGENT_PLUGINS_KEYS = {"$schema", "name", "version", "description", "author", "homepage", "repository", "license",
                      "keywords", "extensions"}
AGENT_PLUGINS_NAME = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")

GUARD_SH = "scripts/stackfoundry.sh"
GUARD_PS1 = "scripts/stackfoundry.ps1"


CODEX_INTERFACE = {
    "displayName": "stackfoundry",
    "shortDescription": "Repo-grounded specialists for every stack in your repository",
    "developerName": "Oleksandr Omelchenko",
    "category": "Coding",
}


def load_claude_manifest() -> dict:
    return json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))


def load_claude_marketplace() -> dict:
    return json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))


def dump(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def check_marketplace_entry(src: dict, market: dict) -> list[str]:
    """The Claude marketplace's entry for the plugin repeats plugin.json's description, so every catalog and the
    installed plugin describe it the same way. The marketplace's own top-level description may differ."""
    entry = next((p for p in market.get("plugins", []) if p.get("name") == src["name"]), None)
    if entry is None:
        return [f".claude-plugin/marketplace.json lists no plugin named {src['name']!r}"]
    if entry.get("description") != src.get("description"):
        return [".claude-plugin/marketplace.json: the plugin entry's description differs from plugin.json's"]
    return []


def check_agent_plugins_manifest(data: dict) -> list[str]:
    """The checks of schemas/agent-plugins-1.0.0/plugin.schema.json, which is closed and small enough to check by hand."""
    errors = [f"unknown key {k!r}" for k in sorted(set(data) - AGENT_PLUGINS_KEYS)]
    for key in ("$schema", "name"):
        if key not in data:
            errors.append(f"missing {key!r}")
    if data.get("$schema") != AGENT_PLUGINS_SCHEMA:
        errors.append("$schema must be the 1.0.0 plugin schema id")
    name = data.get("name", "")
    if not (isinstance(name, str) and 1 <= len(name) <= 64 and AGENT_PLUGINS_NAME.fullmatch(name)):
        errors.append(f"name {name!r} breaks the Agent Plugins name rule")
    for key in ("version", "description", "homepage", "repository", "license"):
        if key in data and not isinstance(data[key], str):
            errors.append(f"{key} must be a string")
    author = data.get("author", {})
    if not isinstance(author, dict) or set(author) - {"name", "email", "url"} or \
            not all(isinstance(v, str) for v in author.values()):
        errors.append("author may hold only string name, email and url")
    if "keywords" in data and not (isinstance(data["keywords"], list) and all(isinstance(k, str) for k in data["keywords"])):
        errors.append("keywords must be a list of strings")
    ext = data.get("extensions", {})
    if not isinstance(ext, dict) or not all(isinstance(v, dict) for v in ext.values()):
        errors.append("extensions must map namespaces to objects")
    return errors


def _metadata(src: dict) -> dict:
    out = {k: src[k] for k in ("name", "version", "description") if k in src}
    if "author" in src:
        out["author"] = {k: v for k, v in src["author"].items() if k in ("name", "email", "url")}
    for k in ("homepage", "repository", "license", "keywords"):
        if k in src:
            out[k] = src[k]
    return out


def guard_command_sh(client: str, root_expr: str) -> str:
    return f'sh "{root_expr}/{GUARD_SH}" guard --client {client}'


def build_plugin_files(src: dict) -> dict[str, str]:
    """Plugin-relative path -> content, for every committed client file inside the plugin folder."""
    files: dict[str, str] = {}

    manifest = {"$schema": AGENT_PLUGINS_SCHEMA, **_metadata(src),
                "extensions": {"com.openai": {"hooks": "./com.openai/hooks.json", "interface": CODEX_INTERFACE}}}
    files["plugin.json"] = dump(manifest)

    # Codex: Claude-compatible hook shape. apply_patch also matches the Edit/Write aliases; ask is not supported
    # there, so the guard turns an ask into a deny with the reason (scripts/stackfoundry/guard.py).
    files["com.openai/hooks.json"] = dump({"hooks": {"PreToolUse": [{
        "matcher": "Bash|apply_patch|Edit|Write",
        "hooks": [{"type": "command",
                   "command": guard_command_sh("codex", "$PLUGIN_ROOT"),
                   "commandWindows": f'pwsh -NoProfile -NonInteractive -File "$env:PLUGIN_ROOT/{GUARD_PS1}" guard --client codex',
                   "timeout": 10,
                   "statusMessage": "stackfoundry guard"}],
    }]}})

    # Copilot: native camelCase event. A preToolUse hook that errors denies the call there, so each command checks
    # that the launcher is where the plugin root says and otherwise exits 0 with no opinion (the launchers also exit
    # 0 when Python is missing). The root variable's name is not documented for hooks: try each known one.
    root_sh = "${PLUGIN_ROOT:-${COPILOT_PLUGIN_ROOT:-$CLAUDE_PLUGIN_ROOT}}"
    root_ps = "$r = @($env:PLUGIN_ROOT, $env:COPILOT_PLUGIN_ROOT, $env:CLAUDE_PLUGIN_ROOT) | Where-Object { $_ } | Select-Object -First 1"
    files["com.github.copilot/hooks/hooks.json"] = dump({"version": 1, "hooks": {"preToolUse": [{
        "type": "command",
        "matcher": "bash|powershell|create|edit|write|str_replace_editor|apply_patch",
        "bash": f'r="{root_sh}"; if [ -n "$r" ] && [ -f "$r/{GUARD_SH}" ]; then sh "$r/{GUARD_SH}" guard --client copilot; fi; exit 0',
        "powershell": f'{root_ps}; if ($r -and (Test-Path -LiteralPath "$r/{GUARD_PS1}")) {{ & pwsh -NoProfile -NonInteractive -File "$r/{GUARD_PS1}" guard --client copilot }}; exit 0',
        "timeoutSec": 10,
    }]}})
    for agent in sorted((PLUGIN / "agents").glob("*.md")):
        files[f"com.github.copilot/agents/{agent.stem}.agent.md"] = render_agent(agent.read_text(encoding="utf-8"), "copilot")

    # Cursor: plugin hooks run from the plugin's install folder, so the launcher path is relative.
    cursor_manifest = {**_metadata(src), "hooks": "./com.cursor/hooks.json"}
    files[".cursor-plugin/plugin.json"] = dump(cursor_manifest)
    cursor_cmd = f"sh ./{GUARD_SH} guard --client cursor"
    files["com.cursor/hooks.json"] = dump({"version": 1, "hooks": cursor_hooks({
        "preToolUse": [{"command": cursor_cmd, "matcher": "Write|Edit|MultiEdit|Delete", "timeout": 10}],
        "beforeShellExecution": [{"command": cursor_cmd, "timeout": 10}],
    })})
    return files


# Cursor runs these plugin hooks from the workspace root, not the plugin's install folder
# (https://cursor.com/docs/agent/hooks): a relative command there would run a script the repo planted (threat model
# T17). Every other plugin hook runs from the install folder, where the relative launcher path is the plugin's own.
CURSOR_WORKSPACE_EVENTS = frozenset({"stop", "subagentStop"})


def cursor_hooks(events: dict) -> dict:
    """The Cursor hook events, refused when a workspace-rooted event's command does not name an absolute path."""
    for event, hooks in events.items():
        if event not in CURSOR_WORKSPACE_EVENTS:
            continue
        for hook in hooks:
            cmd = hook.get("command", "")
            if not re.match(r'\s*\S+\s+"?(\$\{?CURSOR_PLUGIN_ROOT\b|/)', cmd):
                raise ValueError(f"Cursor runs {event} hooks from the workspace root: {cmd!r} must name the launcher "
                                 "through ${CURSOR_PLUGIN_ROOT}, never a relative path")
    return events


def build_marketplace_files(src: dict, market: dict) -> dict[str, str]:
    """Repo-relative path -> content for the marketplace catalogs of Codex, Copilot and Cursor."""
    entry = next(p for p in market["plugins"] if p["name"] == src["name"])
    source = entry["source"]
    owner = market.get("owner", {})
    files: dict[str, str] = {}
    files[".agents/plugins/marketplace.json"] = dump({
        "name": market["name"],
        "interface": {"displayName": market["name"]},
        "plugins": [{"name": src["name"], "source": {"source": "local", "path": source},
                     "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                     "category": CODEX_INTERFACE["category"]}],
    })
    files[".github/plugin/marketplace.json"] = dump({
        "name": market["name"],
        "owner": owner,
        "metadata": {"description": market.get("description", ""), "version": src["version"]},
        "plugins": [{"name": src["name"], "description": entry.get("description", src.get("description", "")),
                     "version": src["version"], "source": source}],
    })
    plugin_root, _, plugin_dir = source.removeprefix("./").rpartition("/")
    files[".cursor-plugin/marketplace.json"] = dump({
        "name": market["name"],
        "owner": owner,
        "metadata": {"description": market.get("description", ""), "version": src["version"],
                     "pluginRoot": plugin_root},
        "plugins": [{"name": src["name"], "source": plugin_dir,
                     "description": entry.get("description", src.get("description", "")),
                     "version": src["version"], "category": entry.get("category", "development"),
                     "tags": entry.get("keywords", [])}],
    })
    return files


def build_gemini(src: dict, out: Path) -> None:
    """A complete Gemini CLI extension at `out` (replaced if it exists)."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "gemini-extension.json").write_text(dump(
        {k: src[k] for k in ("name", "version", "description")}), encoding="utf-8", newline="\n")
    for name in ("skills", "scripts", "reference"):
        shutil.copytree(PLUGIN / name, out / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("README.md", "CHANGELOG.md"):
        shutil.copy2(PLUGIN / name, out / name)
    (out / "agents").mkdir()
    for agent in sorted((PLUGIN / "agents").glob("*.md")):
        (out / "agents" / agent.name).write_text(render_agent(agent.read_text(encoding="utf-8"), "gemini"),
                                                encoding="utf-8", newline="\n")
    (out / "hooks").mkdir()
    (out / "hooks" / "hooks.json").write_text(dump({"hooks": {"BeforeTool": [{
        "matcher": "write_file|replace|run_shell_command",
        "hooks": [{"type": "command", "name": "stackfoundry-guard",
                   "command": 'sh "${extensionPath}${/}scripts${/}stackfoundry.sh" guard --client gemini',
                   "timeout": 10000}],
    }]}}), encoding="utf-8", newline="\n")


def expected() -> dict[Path, str]:
    src = load_claude_manifest()
    files = {PLUGIN / rel: text for rel, text in build_plugin_files(src).items()}
    files.update({ROOT / rel: text for rel, text in build_marketplace_files(src, load_claude_marketplace()).items()})
    return files


def stale_generated(files: dict[Path, str]) -> list[Path]:
    """Generated per-agent files whose source agent is gone."""
    folder = PLUGIN / "com.github.copilot" / "agents"
    return sorted(p for p in folder.glob("*.agent.md") if p not in files) if folder.is_dir() else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="report files that differ; write nothing")
    ap.add_argument("--gemini-out", help="also build the Gemini CLI extension into this folder")
    args = ap.parse_args(argv)

    files = expected()
    problems = check_agent_plugins_manifest(json.loads(files[PLUGIN / "plugin.json"]))
    if problems:
        print("plugin.json breaks Agent Plugins 1.0:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    problems = check_marketplace_entry(load_claude_manifest(), load_claude_marketplace())
    if problems:
        print("\n".join(problems) + " (edit it by hand; this script does not write the Claude catalog)",
              file=sys.stderr)
        return 1
    differ = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    stale = stale_generated(files)
    if args.check:
        for p in differ:
            print(f"out of date: {p.relative_to(ROOT).as_posix()}")
        for p in stale:
            print(f"stale: {p.relative_to(ROOT).as_posix()}")
        if differ or stale:
            print("run: python scripts/build_clients.py", file=sys.stderr)
            return 1
        print(f"build_clients: {len(files)} file(s) current")
        return 0
    for p in differ:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(files[p], encoding="utf-8", newline="\n")
    for p in stale:
        p.unlink()
    print(f"build_clients: wrote {len(differ)}, removed {len(stale)}, {len(files)} file(s) in all")
    if args.gemini_out:
        build_gemini(load_claude_manifest(), Path(args.gemini_out))
        print(f"build_clients: Gemini extension in {args.gemini_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
