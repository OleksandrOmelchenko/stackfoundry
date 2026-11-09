# Changelog

All notable changes to the stackfoundry plugin are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).
A release tag is `stackfoundry--v<version>` (see `docs/release.md` in the repository).

## [Unreleased]

### Added

- Marketplace and plugin manifests, repository setup (CI, pre-commit hook, issue and PR templates).
- The stack model: four layers (language, app model, capability, tooling); one language can carry several app
  models, each with its own rulebook and bug categories.
- `init`, `research-stack`, `sync`, `upgrade`, `materialize`, `configure-guards`: build and maintain a repo profile
  whose technology rules are researched from current sources, cited and grounded in the repo.
- Generic role agents for every role (survey, research, bug hunting, fix verification, the four test roles,
  performance, security, plumbing, debugging, review, docs, benchmarks), reading the profile at run time.
- Work skills: the test quality loop, bug-hunt and fix-verify, review-changes, quality-sweep, security review and
  threat modelling, debug and fix-ci, the backlog and plan lifecycle, the work modes, benchmarks.
- Dependency and radar skills: check-updates, act-on-updates, bump-all, bump, check-formats, tech-radar,
  act-on-radar, radar-digest, stackfoundry-radar, flaky-watch, schedule; github-prs and cleanup-merged.
- The `stackfoundry` helper CLI (Python standard library only, no network) and the guard hook (generated files,
  forbidden commands, git-write policy).
- Eval cases on three fixture repos with planted defects.

### Changed

- Every skill starts from a plain request, in every assistant: no skill is slash-only any more, every description
  ends in a plain-language trigger, and `verify-plumbing` enforces both for plugin skills. Entry points a person
  starts on purpose (init, upgrade, materialize, the act-on skills, github-prs, schedule) say "Only when asked."
- Python 3.11 is the minimum (3.10 reached end of life).
- The stack-researcher writes its pack file itself; init checks it with `stackfoundry pack check` and renders
  rulebooks with `stackfoundry pack render`.
- The survey detects Claude Code plugins and marketplaces, flags fixture folders and reports sources outside every
  manifest; init ignores fixtures and handles `.claude/CLAUDE.md`, the marketplace repo itself and
  non-interactive runs.
- The guard hook sets `onFailure: continue`.
- init checks it can write under `.claude/` before spending anything on research.
- Portability groundwork for Codex, GitHub Copilot, Cursor and Gemini CLI:
  - the repo profile moved from `.claude/stackfoundry/` to `.stackfoundry/`, which every assistant can read and
    which Claude Code does not protect, so researchers write their packs straight into it; `upgrade` moves an old
    profile;
  - the helper CLI's launcher moved from `bin/stackfoundry` to `scripts/stackfoundry.sh`, with
    `scripts/stackfoundry.ps1` for Windows without `sh`; without a top-level `bin/`, claude.ai and Cowork accept the
    plugin;
  - the plugin settings (`userConfig`) became the repo's `.stackfoundry/config.json`, which also lists the
    assistants the repo uses, read with the new `stackfoundry config`;
  - every skill and agent carries a portable-form preamble (the CLI by path, the plugin root where `${CLAUDE_PLUGIN_ROOT}`
    is not substituted, and `reference/clients.md` for tool equivalents), checked by `verify-plumbing` along with the
    Agent Skills name rules.
- The guard answers every assistant's pre-tool hook: `stackfoundry guard` recognizes a Claude Code, Codex, Copilot,
  Cursor or Gemini CLI event (or takes `--client`), reads the files an edit or an `apply_patch` touches, and answers
  in that assistant's format. Where an assistant cannot ask, an ask becomes a deny that says to get the user's
  go-ahead; Cursor, which blocks on empty output, gets an explicit allow when the guard has no opinion.
- Packaging for the other assistants, generated from the Claude Code source by `scripts/build_clients.py` and kept
  current by its `--check` in CI and the pre-commit hook: an Agent Plugins 1.0 `plugin.json` (Codex, Copilot,
  Cursor) with the Codex overlay; Copilot agents with mapped tool grants and its hook; Cursor's manifest and hooks;
  the Codex, Copilot and Cursor marketplaces; and, built on each published release, a Gemini CLI extension.
  `reference/clients.md` maps each assistant's tools, folders, hooks and install commands.
- What `init` writes, per assistant: the repo's `.stackfoundry/config.json` lists its assistants (the survey's new
  `assistants` section proposes them) and `stackfoundry outputs` says where each kind of file goes for them.
  Rulebooks are canonical in `.stackfoundry/rules/` and rendered into Claude Code's `.claude/rules/`, Copilot's
  `.github/instructions/` and Cursor's `.cursor/rules/` (`stackfoundry render-rule`); Codex and Gemini read them
  through the table in `AGENTS.md` and `GEMINI.md`. Team agents are canonical in `.stackfoundry/agents/` and rendered
  for each assistant, Codex's as TOML (`stackfoundry render-agent`). The instruction block template
  (`instructions-block.md`) serves `CLAUDE.md`, `AGENTS.md` and `GEMINI.md`; `globs-check` reads
  `.stackfoundry/rules/` by default; `sync` adds or drops an assistant's files; `schedule` covers the other
  assistants' headless runs.
- A glob with a leading `/` matches at the repo root only, as in `.gitignore`; `docsRoot` lives in
  `.stackfoundry/config.json`, which wins over the older `targets.json` field; init writes its `.claude/` probe and
  its guard probe event with the `Write` tool, since the live guard reads the whole command line.
- The guard reads the nearest `guards.json` above the edited file (worktrees and nested repos), normalizes paths,
  and sees git commands inside quotes (`sh -c 'git push'`).
- The CLI runs git by its absolute path from `PATH`, never a `git` in the repo; `pack render --out` writes atomically;
  every subcommand's help says whether it writes; the survey keeps fixture folders out of its repo-wide counts.

### Fixed

- `guard --check` and `survey` crashed on a `guards.json` or `.claude/settings.json` that is not a JSON object.
- The Agent Plugins name check accepted a trailing newline; a Copilot agent whose grant has no Copilot alias got
  `tools: []` (no tools at all) and now fails the build; MCP tools keep their server in Copilot's form.
- `render-rule` and `render-agent` write atomically; the PowerShell hook commands use `-LiteralPath` and
  `-NonInteractive`.
- A `guards.json` rule could set `"decision": "allow"` and make the guard pre-approve a command; the guard now only
  denies or asks. A usage error on the guard's command line no longer exits 2 (which blocked every tool call).
  `--base` and `--range` values starting with `-` are refused instead of reaching git as options.
- The guard let edits of protected files through when the project path had non-ASCII characters on Windows (the
  hook event was decoded with the code page instead of UTF-8).
- JSON files with a byte-order mark were unreadable (guarding silently stopped).
- Non-ASCII file names dropped out of `change-targets` and `select-tests`.
- Manifest writes were not atomic; `globs-check` ignored `bin/` folders; `verify-plumbing` misread a marketplace
  root; `tracker check` rejected non-tracker files; a bad specialist regex crashed `change-targets`; malformed
  input exited 1 (a verdict) instead of 2.
