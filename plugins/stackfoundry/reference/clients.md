# Assistants (clients)

Every skill and agent is written once, in Claude Code's terms, and runs in each assistant below. This page maps the
Claude Code names and places to the others'. Client ids are the ones `.stackfoundry/config.json` lists under
`clients`. Facts cite their source (bottom); a fact marked *confirm* is not yet proven by the release smoke test in
`docs/release.md` of the stackfoundry repo.

## Tool equivalents

| In a skill or agent | In another assistant |
|---|---|
| `AskUserQuestion` | Its question tool if it has one; otherwise ask in chat, one question per decision, options listed, and wait. |
| `Agent` with `subagent_type: "stackfoundry:<agent>"` | Its subagent or task tool, given the body of `${CLAUDE_PLUGIN_ROOT}/agents/<agent>.md` (below the frontmatter) as the instructions, then the brief. Where it installed the plugin's agents (Copilot, Cursor, Gemini, Antigravity), call that agent by name. No subagents at all: do the agent's work inline, one brief at a time, keeping its output format. |
| `SendMessage` to a dispatched agent | Dispatch again with the earlier result and the follow-up in the brief. |
| `Skill` → `stackfoundry:<skill>` | Run that skill the way the assistant runs skills (by name, or its slash or `$` form). |
| `EnterPlanMode` / `ExitPlanMode` | Write the plan in chat, ask for approval, and change nothing until it is given. |
| `Bash` with `run_in_background` | Run it and wait; report how long it took. |
| `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`, `PowerShell` | Its file-read, search, edit, write and shell tools. |
| `WebSearch`, `WebFetch` | Its web tools. Without any, research cannot run: say so and stop, never fill facts from memory. |
| `${CLAUDE_PLUGIN_ROOT}` | The plugin's installed folder: two levels above a skill's folder, or the `pluginRoot:` in an agent's brief. |
| `${CLAUDE_PROJECT_DIR}` | The repository root. |

## Where each assistant looks

| | Claude Code | Codex | GitHub Copilot (CLI, VS Code) | Cursor | Gemini CLI | Antigravity CLI |
|---|---|---|---|---|---|---|
| Plugin manifest | `.claude-plugin/plugin.json` | `plugin.json` (Agent Plugins 1.0), legacy `.codex-plugin/plugin.json` | `plugin.json` (Agent Plugins 1.0), then `.plugin/`, `.github/plugin/`, `.claude-plugin/` | `.cursor-plugin/plugin.json`, or `plugin.json` (Agent Plugins: skills and MCP only) | `gemini-extension.json` (an extension, not a plugin) | `plugin.json`, or `.antigravity-plugin/plugin.json` first; its own schema, not Agent Plugins 1.0 [ag-build-plugins] |
| Marketplace file | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json`, legacy `.claude-plugin/marketplace.json` | `marketplace.json`, `.plugin/`, `.github/plugin/`, `.claude-plugin/` (in that order) | `.cursor-plugin/marketplace.json` | none: install by repository URL or release | its official marketplace (`<name>@antigravity-plugins-official`); otherwise install by URL or path [ag-plugins] |
| Add and install | `claude plugin marketplace add <owner/repo>`, `claude plugin install stackfoundry@stackfoundry` | `codex plugin marketplace add <owner/repo>`, then its plugins list | `copilot plugin marketplace add <owner/repo>`, `copilot plugin install stackfoundry@stackfoundry` | its marketplace, a team marketplace, or `~/.cursor/plugins/local` | `gemini extensions install <url>` | `agy plugin install <url or folder>`; `agy plugin import gemini` converts installed Gemini extensions [ag-plugins], [ag-gcli-migration] |
| Plugin root in hooks | `${CLAUDE_PLUGIN_ROOT}` | `PLUGIN_ROOT` (also sets `CLAUDE_PLUGIN_ROOT`) | `PLUGIN_ROOT` | `CURSOR_PLUGIN_ROOT`; plugin hooks run from the install folder, except `stop` and `subagentStop` (workspace root) | `${extensionPath}` | hooks run with the plugin root as working directory, so commands are relative [ag-build-plugins] |
| Plugin subagents | `agents/*.md` | not shipped by plugins | `com.github.copilot/agents/*.agent.md` | `agents/*.md` | `agents/*.md` (preview) | `agents/<name>.md` with a `tools` allowlist [ag-build-plugins] |
| Plugin hooks | `hooks/hooks.json` | `hooks/hooks.json` or `extensions.com.openai.hooks` (manually installed plugins only) | `com.github.copilot/hooks/hooks.json` | `hooks/hooks.json` or the manifest's `hooks` | `hooks/hooks.json` | root `hooks.json`, one named entry per hook [ag-hooks] |
| Repo skills | `.claude/skills/` | `.agents/skills/` | `.github/skills/`, `.claude/skills/` | `.cursor/skills/`, `.agents/skills/`, `.claude/skills/`, `.codex/skills/` | `.gemini/skills/`, `.agents/skills/` (*confirm*) | `.agents/skills/` [ag-rules] |
| Repo subagents | `.claude/agents/*.md` | `.codex/agents/*.toml` (`name`, `description`, `developer_instructions`) | `.github/agents/*.agent.md`, `.claude/agents/` | `.cursor/agents/`, `.claude/agents/`, `.codex/agents/` | `.gemini/agents/*.md` | none documented |
| Rules scoped by path | `.claude/rules/*.md` with `paths:` | none | `.github/instructions/*.instructions.md` with `applyTo:` | `.cursor/rules/*.mdc` with `globs:` | none | `.agents/rules/*.md` with `trigger: glob` and `globs:` (one comma-separated string) [ag-rules] |
| Instruction file | `CLAUDE.md` (root or `.claude/`) | `AGENTS.md` (nested files apply below them) | `AGENTS.md`, `.github/copilot-instructions.md` | `AGENTS.md` | `GEMINI.md` (setting `context.fileName` can add `AGENTS.md`) | `AGENTS.md` or `GEMINI.md`, from the launch folder up to the repo root [ag-rules] |
| Headless run | `claude -p "<prompt>"` | `codex exec "<prompt>"` | `copilot -p "<prompt>"` | `cursor-agent -p "<prompt>"` | `gemini -p "<prompt>"` | `agy -p "<prompt>"` [ag-cli] |

## The guard in each assistant

One command, `stackfoundry guard`, serves every assistant's pre-tool hook. It recognizes the event (or takes
`--client`), applies `.stackfoundry/guards.json`, and answers in that assistant's format:

| Assistant | Hook event | Edits it sees | It cannot ask, so an ask becomes | No opinion is |
|---|---|---|---|---|
| Claude Code | `PreToolUse` | `Edit`, `Write`, `MultiEdit`, `NotebookEdit` | (asks) | no output |
| Codex | `PreToolUse` | `apply_patch` (every file the patch names) | a deny saying to get the user's go-ahead | no output |
| Copilot | `preToolUse` | `create`, `edit`, `str_replace_editor`, `apply_patch`; also `write`, matched in case it is sent | (asks; its autopilot denies an ask, and its cloud agent loads no plugin hooks) | no output |
| Cursor | `preToolUse` for edits, `beforeShellExecution` for commands | `Write`, `Edit`, `Delete` | a deny for edits (commands can ask) | `{"permission": "allow"}`: Cursor blocks on empty output |
| Gemini CLI | `BeforeTool` | `write_file`, `replace` | a deny saying to get the user's go-ahead | no output |
| Antigravity CLI | `PreToolUse` | `write_to_file`, `replace_file_content`, `multi_replace_file_content` (`TargetFile`); commands are `run_command` (`CommandLine`, `Cwd`) | (asks with `force_ask`, which a cached "Always Allow" cannot skip) | no output |

**Antigravity CLI** sends `toolCall.name` and `toolCall.args` and reads `{"decision": "deny"|"force_ask", "reason":
…}` [ag-hooks]. A hook that exits non-zero is logged and ignored, so the call goes through [ag-build-plugins]: the
guard always exits 0, with a decision in JSON or no output for no opinion. Plugin hooks run from the plugin root, so the command names the launcher
relative to it (`sh ./scripts/stackfoundry.sh`, built by `scripts/build_clients.py` `antigravity_hooks`). On
Windows that needs `sh` (Git Bash): without it the hook fails and the call goes through unguarded. Gemini CLI still serves Gemini Code Assist Standard and Enterprise and paid API keys; individual
tiers moved to Antigravity CLI on 2026-06-18 [google-antigravity], [gemini-cli-readme].

Each assistant's hook file is generated (`plugin.json` → `com.openai/hooks.json`, `com.github.copilot/hooks/`,
`com.cursor/hooks.json`, the Gemini extension's `hooks/hooks.json`). Copilot denies a tool call when a hook errors,
so its hook command exits 0 with no opinion when it cannot find the launcher. Claude Code runs a shell-form hook in
PowerShell when Git Bash is missing ([hooks](https://code.claude.com/docs/en/hooks)), where `sh` does not exist; the
hook sets `"onFailure": "continue"`, so the call goes through with no guard rather than being blocked.
`stackfoundry guard --check` warns when `sh` is missing on Windows. Cursor runs plugin hooks from the plugin's
install folder, so its guard command names the launcher relative to it; `stop` and `subagentStop` plugin hooks run
from the workspace root instead ([cursor-hooks](https://cursor.com/docs/agent/hooks)), so `scripts/build_clients.py`
`cursor_hooks` refuses a relative command for them. *Confirm* in each assistant before
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
  to the working directory) through Write and Edit alike. A `Write(...)` rule allows nothing.
- **The launcher:** `"Bash(sh \"<plugin root>/scripts/stackfoundry.sh\" *)"`, quoted exactly as called, is allowed;
  a `*` inside the path does not match.
- **Subagents:** a subagent runs under the same rules, so a `web-researcher` reads only the hosts allowed as
  `WebFetch(domain:…)`.
- **Confirmed:** each of these with a headless run on Claude Code 2.1.

## Rules where there is no path scoping

Where an assistant has no path-scoped rules (Codex, Gemini), stackfoundry writes each rulebook to
`.stackfoundry/rules/<id>.md` and lists it in the instruction-file block with the globs it covers: read it before
editing a matching file.

Only a file such an assistant reads gets that table. Where every reader loads the rulebooks by itself (Claude
Code, Copilot, Cursor, Antigravity, each with a copy of every rulebook in its own folder), the block is a short
pointer to the profile. A host whose copies the repo does not keep is told to read the rulebooks, like Codex. A
table too large for the block (`scripts/stackfoundry/block.py` `BLOCK_BUDGET`) goes to `.stackfoundry/rulebooks.md`,
which the block links, so Codex's 32 KiB is not spent on it. An instruction file is loaded
into every session, and Claude Code's guidance is to keep it short and move part-of-the-codebase instructions
into path-scoped rules, which load on a Read, Write or Edit of a matching file [cc-memory].

## Size limits

What each host advises or enforces on what it loads. `scripts/stackfoundry/clients.py` `LIMITS` holds the numbers, and
`stackfoundry size-check` applies them to a repo's generated files: past a hard limit is an error, past advice a
warning, and every file's lines, bytes and estimated tokens are listed.

| Host | What | Limit | Kind | Source |
|---|---|---|---|---|
| Claude Code | a `CLAUDE.md` | 200 lines | advice | [cc-memory] |
| Cursor | a rule | 500 lines | advice | [cursor-rules] |
| Every assistant (Agent Skills) | a `SKILL.md` | 500 lines, about 5000 tokens | advice | [skills-spec] |
| Codex | the `AGENTS.md` files on a path, combined | 32 KiB | stops reading | [codex-agents-md] |
| Antigravity CLI | a rule file in `.agents/rules/` | 24,000 bytes | truncated | [ag-rules] |
| Antigravity CLI | every always-on rule and instruction file, combined | 20,000 tokens | the largest become pointers | [ag-rules] |

The plugin's own listing (every skill and agent description, loaded each session) has a budget too:
`scripts/stackfoundry/plumbing.py` `LISTING_CAP`, enforced by `verify-plumbing` in plugin mode.

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
- [cc-memory] Claude Code memory (CLAUDE.md size advice): https://code.claude.com/docs/en/memory
- [cursor-rules] Cursor rules (rule size advice): https://cursor.com/docs/context/rules
- [skills-spec] Agent Skills specification (SKILL.md size advice): https://agentskills.io/specification
- [codex-agents-md] Codex AGENTS.md (combined size limit): https://learn.chatgpt.com/docs/agent-configuration/agents-md
- [cursor-hooks] Cursor hooks (where plugin hooks run): https://cursor.com/docs/agent/hooks

Antigravity CLI and the Gemini CLI transition, accessed 2026-11-11:

- [google-antigravity] Google, transitioning Gemini CLI to Antigravity CLI:
  https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/
- [gemini-cli-readme] Gemini CLI repository README (who it still serves): https://github.com/google-gemini/gemini-cli
- [ag-plugins] Antigravity plugins (install, marketplace): https://antigravity.google/docs/plugins?tab=cli
- [ag-build-plugins] Antigravity, build plugins (manifest, layout, agents, skills, hooks' working directory and exit
  codes): https://antigravity.google/docs/build-plugins/
- [ag-hooks] Antigravity hooks (events, input, decisions): https://antigravity.google/docs/hooks?tab=cli
- [ag-rules] Antigravity rules (instruction files, `.agents/rules`, size limits): https://antigravity.google/docs/rules?tab=cli
- [ag-gcli-migration] Antigravity, migrating from Gemini CLI: https://antigravity.google/docs/cli/gcli-migration
- [ag-cli] Antigravity CLI reference (headless flags): https://antigravity.google/docs/cli/reference
- [ag-sdk-tools] Antigravity built-in tools (`search_web`, `read_url_content`): https://www.antigravity.google/docs/sdk/tools/
