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
- The guard reads the nearest `guards.json` above the edited file (worktrees and nested repos), normalizes paths,
  and sees git commands inside quotes (`sh -c 'git push'`).
- The CLI runs git by its absolute path from `PATH`, never a `git` in the repo; `pack render --out` writes atomically;
  every subcommand's help says whether it writes; the survey keeps fixture folders out of its repo-wide counts.

### Fixed

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
