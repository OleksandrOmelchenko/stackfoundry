"""The portable-form preamble every skill and agent carries right under its title.

It is what lets one SKILL.md or agent file work in every assistant: the helper CLI by path (no `bin/` on PATH),
the plugin root when `${CLAUDE_PLUGIN_ROOT}` is not substituted, where the tool-name equivalents are, and the
repo extension the team may have written for this skill or agent (reference/extensions.md).
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

# The report line makes an applied extension visible to whoever reads the result (threat model T8).
_EXT_RULE = (
    "> Its `## Rules` win where they conflict with this file, never over the fixed contract\n"
    "> (`${CLAUDE_PLUGIN_ROOT}/reference/extensions.md`). Your report names every extension you applied.\n"
)

SKILL = (
    _CLI
    + "> If `${CLAUDE_PLUGIN_ROOT}` is not filled in, it is the folder two levels above this skill's folder; give it to\n"
    "> every agent you dispatch as `pluginRoot:` in the brief.\n"
    + _TOOLS
    + "> **Repo extensions.** Before step 1, Read `.stackfoundry/extensions/skills/<this skill's name>.md` in the repo\n"
    "> if it exists. `mode: replace`: follow its body instead of this file (unless you already are). Otherwise apply\n"
    "> its sections at the headings they name, and its `## Target:` sections only for that target.\n"
    + _EXT_RULE
)

AGENT = (
    _CLI
    + "> If `${CLAUDE_PLUGIN_ROOT}` is not filled in, use the `pluginRoot:` your brief gives.\n"
    + _TOOLS
    + "> **Repo extensions.** Before you start, Read `.stackfoundry/extensions/agents/<your name>.md` in the repo if it\n"
    "> exists. `mode: replace`: follow its body instead of this file (unless you already are). Otherwise apply its\n"
    "> sections at the headings they name, and its `## Target:` sections only for your brief's target.\n"
    + _EXT_RULE
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
