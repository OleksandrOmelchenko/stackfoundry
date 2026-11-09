"""The portable-form preamble every skill and agent carries right under its title.

It is what lets one SKILL.md or agent file work in every assistant: the helper CLI by path (no `bin/` on PATH),
the plugin root when `${CLAUDE_PLUGIN_ROOT}` is not substituted, and where the tool-name equivalents are.
`verify-plumbing` checks that each file carries the current text exactly.
"""
from __future__ import annotations

_CLI = (
    "> **Portable form.** `stackfoundry <subcommand>` here means\n"
    "> `sh \"${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.sh\" <subcommand>` (Windows without `sh`:\n"
    "> `pwsh -NoProfile -File \"${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.ps1\" <subcommand>`).\n"
)
_TOOLS = (
    "> Tool names are Claude Code's; in another assistant use its equivalent\n"
    "> (`${CLAUDE_PLUGIN_ROOT}/reference/clients.md`).\n"
)

SKILL = (
    _CLI
    + "> If `${CLAUDE_PLUGIN_ROOT}` is not filled in, it is the folder two levels above this skill's folder; give it to\n"
    "> every agent you dispatch as `pluginRoot:` in the brief.\n"
    + _TOOLS
)

AGENT = (
    _CLI
    + "> If `${CLAUDE_PLUGIN_ROOT}` is not filled in, use the `pluginRoot:` your brief gives.\n"
    + _TOOLS
)


def insert(text: str, preamble: str) -> str:
    """The file with the preamble placed (or replaced) right after its first `# ` title."""
    lines = text.split("\n")
    # Drop an existing preamble block, wherever it is.
    out, i = [], 0
    while i < len(lines):
        if lines[i].startswith("> **Portable form.**"):
            while i < len(lines) and lines[i].startswith(">"):
                i += 1
            if i < len(lines) and lines[i] == "" and out and out[-1] == "":
                i += 1
            continue
        out.append(lines[i])
        i += 1
    for j, line in enumerate(out):
        if line.startswith("# "):
            block = preamble.rstrip("\n").split("\n")
            return "\n".join(out[: j + 1] + [""] + block + out[j + 1:])
    raise ValueError("no '# ' title to put the preamble under")
