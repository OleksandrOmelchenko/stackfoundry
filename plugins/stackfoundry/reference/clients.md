# Assistants (clients)

Every skill and agent is written once, in Claude Code's terms, and runs in each assistant below. This page maps the
Claude Code names and places to the others'. Client ids are the ones `.stackfoundry/config.json` lists under
`clients`. Facts cite their source (bottom); a fact marked *confirm* is not yet proven by the release smoke test in
`docs/release.md` of the stackfoundry repo.

## Tool equivalents

| In a skill or agent | In another assistant |
|---|---|
| `AskUserQuestion` | Its question tool if it has one; otherwise ask in chat, one question per decision, options listed, and wait. |
| `Agent` with `subagent_type: "stackfoundry:<agent>"` | Its subagent or task tool, given the body of `${CLAUDE_PLUGIN_ROOT}/agents/<agent>.md` (below the frontmatter) as the instructions, then the brief. Where it installed the plugin's agents (Copilot, Cursor, Gemini), call that agent by name. No subagents at all: do the agent's work inline, one brief at a time, keeping its output format. |
| `SendMessage` to a dispatched agent | Dispatch again with the earlier result and the follow-up in the brief. |
| `Skill` → `stackfoundry:<skill>` | Run that skill the way the assistant runs skills (by name, or its slash or `$` form). |
| `EnterPlanMode` / `ExitPlanMode` | Write the plan in chat, ask for approval, and change nothing until it is given. |
| `Bash` with `run_in_background` | Run it and wait; report how long it took. |
| `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`, `PowerShell` | Its file-read, search, edit, write and shell tools. |
| `WebSearch`, `WebFetch` | Its web tools. Without any, research cannot run: say so and stop, never fill facts from memory. |
| `${CLAUDE_PLUGIN_ROOT}` | The plugin's installed folder: two levels above a skill's folder, or the `pluginRoot:` in an agent's brief. |
| `${CLAUDE_PROJECT_DIR}` | The repository root. |

## Where each assistant looks

| | Claude Code | Codex | GitHub Copilot (CLI, VS Code) | Cursor | Gemini CLI |
|---|---|---|---|---|---|
| Plugin manifest | `.claude-plugin/plugin.json` | `plugin.json` (Agent Plugins 1.0), legacy `.codex-plugin/plugin.json` | `plugin.json` (Agent Plugins 1.0), then `.plugin/`, `.github/plugin/`, `.claude-plugin/` | `.cursor-plugin/plugin.json`, or `plugin.json` (Agent Plugins: skills and MCP only) | `gemini-extension.json` (an extension, not a plugin) |
| Marketplace file | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json`, legacy `.claude-plugin/marketplace.json` | `marketplace.json`, `.plugin/`, `.github/plugin/`, `.claude-plugin/` (in that order) | `.cursor-plugin/marketplace.json` | none: install by repository URL or release |
| Add and install | `claude plugin marketplace add <owner/repo>`, `claude plugin install stackfoundry@stackfoundry` | `codex plugin marketplace add <owner/repo>`, then its plugins list | `copilot plugin marketplace add <owner/repo>`, `copilot plugin install stackfoundry@stackfoundry` | its marketplace, a team marketplace, or `~/.cursor/plugins/local` | `gemini extensions install <url>` |
| Plugin root in hooks | `${CLAUDE_PLUGIN_ROOT}` | `PLUGIN_ROOT` (also sets `CLAUDE_PLUGIN_ROOT`) | `PLUGIN_ROOT` | `${CURSOR_PLUGIN_ROOT}` / `${CLAUDE_PLUGIN_ROOT}` in MCP config; hooks: *confirm* | `${extensionPath}` |
| Plugin subagents | `agents/*.md` | not shipped by plugins | `com.github.copilot/agents/*.agent.md` | `agents/*.md` | `agents/*.md` (preview) |
| Plugin hooks | `hooks/hooks.json` | `hooks/hooks.json` or `extensions.com.openai.hooks` (manually installed plugins only) | `com.github.copilot/hooks/hooks.json` | `hooks/hooks.json` or the manifest's `hooks` | `hooks/hooks.json` |
| Repo skills | `.claude/skills/` | `.agents/skills/` | `.github/skills/`, `.claude/skills/` | `.cursor/skills/`, `.agents/skills/`, `.claude/skills/`, `.codex/skills/` | `.gemini/skills/`, `.agents/skills/` (*confirm*) |
| Repo subagents | `.claude/agents/*.md` | `.codex/agents/*.toml` (`name`, `description`, `developer_instructions`) | `.github/agents/*.agent.md`, `.claude/agents/` | `.cursor/agents/`, `.claude/agents/`, `.codex/agents/` | `.gemini/agents/*.md` |
| Rules scoped by path | `.claude/rules/*.md` with `paths:` | none | `.github/instructions/*.instructions.md` with `applyTo:` | `.cursor/rules/*.mdc` with `globs:` | none |
| Instruction file | `CLAUDE.md` (root or `.claude/`) | `AGENTS.md` (nested files apply below them) | `AGENTS.md`, `.github/copilot-instructions.md` | `AGENTS.md` | `GEMINI.md` (setting `context.fileName` can add `AGENTS.md`) |
| Headless run | `claude -p "<prompt>"` | `codex exec "<prompt>"` | `copilot -p "<prompt>"` | `cursor-agent -p "<prompt>"` | `gemini -p "<prompt>"` |

## The guard in each assistant

One command, `stackfoundry guard`, serves every assistant's pre-tool hook. It recognizes the event (or takes
`--client`), applies `.stackfoundry/guards.json`, and answers in that assistant's format:

| Assistant | Hook event | Edits it sees | It cannot ask, so an ask becomes | No opinion is |
|---|---|---|---|---|
| Claude Code | `PreToolUse` | `Edit`, `Write`, `MultiEdit`, `NotebookEdit` | (asks) | no output |
| Codex | `PreToolUse` | `apply_patch` (every file the patch names) | a deny saying to get the user's go-ahead | no output |
| Copilot | `preToolUse` | `create`, `edit`, `str_replace_editor`, `apply_patch` | (asks; its autopilot denies an ask, and its cloud agent loads no plugin hooks) | no output |
| Cursor | `preToolUse` for edits, `beforeShellExecution` for commands | `Write`, `Edit`, `Delete` | a deny for edits (commands can ask) | `{"permission": "allow"}`: Cursor blocks on empty output |
| Gemini CLI | `BeforeTool` | `write_file`, `replace` | a deny saying to get the user's go-ahead | no output |

Each assistant's hook file is generated (`plugin.json` → `com.openai/hooks.json`, `com.github.copilot/hooks/`,
`com.cursor/hooks.json`, the Gemini extension's `hooks/hooks.json`). Copilot denies a tool call when a hook errors,
so its hook command exits 0 with no opinion when it cannot find the launcher. *Confirm* in each assistant before
relying on it: which variable carries the plugin root in Copilot's plugin hooks, whether Cursor's `allow` leaves its
own approval prompts in place, and that Codex runs hooks from a marketplace install (its docs limit plugin hooks to
manual installs, after `/hooks` trust).

**Which agent made the call.**
- **Claude Code:** gives a hook the calling subagent as `agent_type`. For a plugin agent that is the plugin-scoped
  name, such as `stackfoundry:product-analyst`; for a repo agent it is the bare name. The main session sends none
  [claude-code-hooks]; confirmed with a headless run on Claude Code 2.1.
- **The role rules** (`guard.py`, *Roles*) use that field: the asks for read-only roles, the control-plane files and
  the researchers' own outputs.
- **Other assistants:** they don't send the field, so the rules don't apply there and those roles stay bound by
  their instructions only.

**Unattended Claude Code runs.**
- **Permission flags:** `--permission-mode dontAsk` denies every call that would prompt; only the allowed rules run
  [claude-code-permissions].
- **Path rules:** on the command line, `--allowedTools "Edit(docs/radar/**)"` allows writes to that folder (relative
  to the working directory) through Write and Edit alike. A `Write(...)` rule allows nothing. Both confirmed with a
  headless run on Claude Code 2.1.

## Rules where there is no path scoping

Where an assistant has no path-scoped rules (Codex, Gemini), stackfoundry writes each rulebook to
`.stackfoundry/rules/<id>.md` and lists it in the instruction-file block with the globs it covers: read it before
editing a matching file.

## Sources (accessed 2026-11-09)

- [claude-code] Claude Code plugin manifest reference: https://code.claude.com/docs/en/plugins-reference
- [claude-code-hooks] Claude Code hooks reference (`agent_type`, `agent_id`): https://code.claude.com/docs/en/hooks
- [claude-code-permissions] Claude Code permissions (modes, rule syntax): https://code.claude.com/docs/en/permissions
- [agent-skills] Agent Skills specification and client guide: https://agentskills.io/specification,
  https://agentskills.io/client-implementation/adding-skills-support
- [agent-plugins] Agent Plugins specification 1.0.0: https://github.com/agentplugins/agent-plugins-spec
- [codex] Codex, package your plugin: https://developers.openai.com/codex/plugins/build
- [copilot] Copilot CLI plugin reference: https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference
- [cursor] Cursor plugins reference and skills: https://cursor.com/docs/reference/plugins, https://cursor.com/docs/skills
- [gemini] Gemini CLI extension reference: https://geminicli.com/docs/extensions/reference/
