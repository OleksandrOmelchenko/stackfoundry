# Antigravity CLI channel

**Category:** plugin

**Status:** built. The real `agy` smoke test has not been run.

## Why

Google moved individual Gemini CLI users to Antigravity CLI (`agy`). Gemini CLI kept serving Gemini Code Assist
Standard and Enterprise and paid API keys, and it is still released. Antigravity uses its own plugin format, and an
installed Gemini extension doesn't carry over unchanged. So people following stackfoundry from Gemini CLI had no
working install with the guard. The format and its sources are in `plugins/stackfoundry/reference/clients.md`
(the Antigravity CLI column and *Sources*).

The decision was to add Antigravity CLI as a channel and keep the Gemini extension.

## Behaviour

- **The plugin.** Every published release attaches `stackfoundry-antigravity.tar.gz`, built by
  `scripts/build_clients.py --antigravity-out <dir>`. It installs with `agy plugin install <extracted folder>`. The
  tree holds:
  - `plugin.json`, with only the keys Antigravity's manifest schema allows;
  - the skills, with only the frontmatter keys Antigravity documents for a skill, each named for its folder;
  - the agents, each with an Antigravity tool allowlist mapped from its Claude Code grant;
  - `scripts/`, `reference/`, the README and the CHANGELOG;
  - a root `hooks.json`, whose `stackfoundry-guard` `PreToolUse` hook matches `run_command`, `write_to_file`,
    `replace_file_content` and `multi_replace_file_content`. It runs `sh ./scripts/stackfoundry.sh guard --client
    antigravity`, because Antigravity runs plugin hooks from the plugin root.
- **The guard.** An event with `toolCall` is Antigravity's. Edits take their path from `TargetFile`, and commands
  take `CommandLine` and `Cwd`. The repo comes from `workspacePaths`, since the process's own folder is the plugin.
  - The answer is `{"decision": "deny"|"ask", "reason": …}`, and asks are kept.
  - It always exits 0, because Antigravity ignores a hook that fails.
  - On Windows without `sh`, the hook fails and the call goes through unguarded, as with Claude Code.
- **The repo client `antigravity`** (`config.json` `clients`):
  - rulebook copies go in `.agents/rules/<id>.md` as `trigger: glob` rules, with one quoted, comma-separated `globs`
    string;
  - skills go in `.agents/skills/`;
  - its stackfoundry block goes in `AGENTS.md`, shared with Codex and Copilot, with its own loading sentence;
  - it gets no project agents, because Antigravity documents no project agents folder;
  - `render-agent --client antigravity` refuses a grant with no Antigravity equivalent, because an agent without
    `tools` would get every tool;
  - `size-check` errors when a rule file or `AGENTS.md` passes 24,000 bytes, where Antigravity truncates.
- **Gemini CLI** keeps its release asset. The README says who Gemini CLI still serves, and tells people moving to
  Antigravity to install the plugin rather than `agy plugin import gemini`, which carries no guard hook.
- **The radar.** `stackfoundry-radar` checks each assistant in `clients` for retirements, format changes and
  successors, so the next such move shows up in a report.

## Design

- **Builder**, `scripts/build_clients.py`: `build_antigravity`, `antigravity_skill`, `antigravity_hooks`,
  `ANTIGRAVITY_MANIFEST_KEYS`, `ANTIGRAVITY_SKILL_KEYS` and `ANTIGRAVITY_GUARDED_TOOLS`.
- **Guard**, `plugins/stackfoundry/scripts/stackfoundry/guard.py`: `detect`, `normalize`, `answer` and
  `_project_dir`.
- **Clients**, `plugins/stackfoundry/scripts/stackfoundry/clients.py`:
  - `CLIENTS`, `RULE_FORMATS`, `INSTRUCTION_FILES`, `LIMITS` and `ANTIGRAVITY_TOOLS`;
  - `render_rule` and `render_agent`;
  - `agent_path`, which refuses a client with no agents folder.
- **Other code:** `block.py` `NAMES`, the `cli.py` client choices, and `reference/schemas/config.schema.json`.
- **Release:** `.github/workflows/release.yml`, job `antigravity`.

## Verification

- **Guard:** `tests/test_guard_clients.py` `AntigravityTests` sends recorded events for every edit tool, a relative
  target, an asked git write, a denied command and no opinion. The detection case is there too.
- **Repo client:** `tests/test_antigravity.py` covers outputs, the rule and agent formats, the size limit and the
  block sentence.
- **Built plugin:** `tests/test_antigravity.py` `PluginBundleTests` checks the manifest keys, the skill names and
  keys, every agent's allowlist, the hook matching exactly the tools the guard maps, and the relative launcher.
- **Run by hand:** the built hook command, run from the built plugin folder against a scratch repo, denied a
  generated-file write, asked before a git commit, and gave no opinion on a plain write.
- **Gates:** the `cli` and `plugin` gates were green.

## Follow-ups (not yet implemented)

- The real smoke test once `agy` is installed: `agy plugin validate --strict`, install, the skills and agents
  listed, a guard denial, and a plain request starting a skill (the `docs/release.md` Antigravity row).
- Confirm on a real install that unknown agent frontmatter and the skills' `${CLAUDE_PLUGIN_ROOT}` references work.
  The skills already fall back to "two levels above this skill's folder".
