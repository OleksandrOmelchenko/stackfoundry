# Changelog

All notable changes to the stackfoundry plugin are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).
A release tag is `stackfoundry--v<version>` (see `docs/release.md` in the repository).

## [Unreleased]

### Security

- `stackfoundry extensions` no longer trusts the paths in a committed `.stackfoundry/extensions/.base/index.json`.
  Before this fix, a hostile repo could make `merge` copy a local file (an SSH key, say) into a tracked extension.
  It could also make `merge` overwrite, or `forget` delete, files outside `.stackfoundry/`.
- The CLI now handles the index this way:
  - Base copies are derived from their file's path.
  - A source must name a plugin skill or agent.
  - Every path is checked after resolving links.
  - `extensions check` reports a bad entry as an error.
- The rule is in `reference/extensions.md` ("What the index is trusted with"). Threat model T4.
- **Git and gh writes** (T5): the guard parses each command before judging it, so it catches forms it missed before:
  - quoted or repeated `-C`, `-c`, `--no-pager`;
  - `git.exe` and path-prefixed git;
  - `git pull`, branch creation, worktree, notes and ref writes, and `git config core.hooksPath`;
  - `gh api` with fields or a non-GET method, and more gh verbs.

  It no longer flags `echo 'git push'`.
- **Nested `guards.json`** (T6): every file from the call's folder up, plus the project root's, applies, and the
  strictest answer wins. An empty, partial or broken nested file can no longer switch off the root's rules.
- **Role rules** (T3, T11): in Claude Code the guard knows which subagent made a call. It asks before:
  - a read-only role changes project files;
  - any subagent changes a control-plane file (`.stackfoundry/**`, instruction files) its role does not own;
  - a web-reading researcher writes beyond its output.
- **Shell and web apart** (T2, T15): `security-reviewer` and `performance-reviewer` no longer hold web tools, and
  `tech-radar` no longer sends all-tool agents onto web pages. `verify-plumbing` rejects any grant that holds a shell
  beside web tools.
- **Unattended runs** (T11, T16): `schedule` now proposes `--permission-mode dontAsk` with an allow list, replacing
  `acceptEdits`. The side-effect check now covers untracked files and the control plane's content.
- **Researched text** (T9): pack and brief text must be single-line and free of HTML comments, rulebook paths must be
  plain globs, and rendering cannot break out of a line. init and research-stack show a new pack's rules before
  writing.

### Added

- The `web-researcher` agent: it answers a skill's web questions with cited notes, and holds no shell and writes
  nothing.
- `stackfoundry side-effects start|end`, and `reference/unattended.md`, the one copy of the unattended-run contract.
- `configure-guards` and `init` offer Claude Code `ask` rules for `guards.json` and `extensions/**`.

### Changed

- `security-reviewer` and `performance-reviewer` grants dropped `WebSearch` and `WebFetch`. Their skills pass
  `web-researcher` notes as `web:`, and `performance-review` writes Pass 2 itself. A materialized copy picks up the
  grant change through `upgrade`'s three-way merge.
- `performance-review` gained a step, *Web pass*, before *Persist*.
- **Breaking for scheduled runs:** existing cron or Actions lines that use `acceptEdits` keep working. Re-run
  `/stackfoundry:schedule` to move them to the bounded line.

### Fixed

- `stackfoundry today` dates a `UTC` (or `Etc/UTC`) profile in UTC even when Python has no zone database. Windows
  Python without the `tzdata` package used to fall back to the machine's local date. For other zones the fallback
  now says to install `tzdata`.

## [0.2.0] - 2026-11-09

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
- `walkthrough`: a guided tour by questions that finds the right skill for what the user wants, teaches the plain
  request that starts it, and runs it with their yes. `verify-plumbing` checks its group table names every skill.
- Repo extensions (`reference/extensions.md`): a team changes a plugin skill or agent in
  `.stackfoundry/extensions/`, which every skill and agent reads before it starts and which plugin updates never
  overwrite. `extend` files add anchored sections; `replace` files and materialized agents keep a base copy so
  `upgrade` three-way merges the plugin's changes into them. New `customize` skill, `stackfoundry extensions
  list|check|new|base|merge|forget`, and an extensions step in `upgrade` and `stackfoundry-radar`. `walkthrough`
  tells users every skill can be customized and marks the ones this repo changed.
- `whats-next`: the next product and technical steps for any kind of product, ranked by risk and value and
  weighted by the targets' stakes, each with a domain source and a repo path; picked items become backlog plans,
  and `--report` runs quarterly from `schedule`. It reads `.stackfoundry/product.json` (what kind of product this
  is: inferred by the surveyor, confirmed at init, watched by sync) and a researched, cited domain brief
  (`.stackfoundry/domain/<id>.json`: table-stakes, expected and differentiating capabilities, regulations, metrics,
  failure patterns, trends). New agents `domain-researcher` and `product-analyst`, procedure
  `reference/product-research.md`, schemas `product` and `domain`, and `stackfoundry product check|status`.

### Changed

- Every skill starts from a plain request, in every assistant: no skill is slash-only any more, every description
  ends in a plain-language trigger, and `verify-plumbing` enforces both for plugin skills. Entry points a person
  starts on purpose (init, upgrade, materialize, the act-on skills, github-prs, schedule) say "Only when asked."
- The scheduled checks are visible: the README's "Keep watching your stack" lists what each unattended report gives
  (stack news from tech-radar, outdated pins, plugin drift, flaky tests, doc drift) and its follow-up request;
  walkthrough groups them under "Stay current", says a schedulable skill can run on a timer, and offers
  "Schedule it". tech-radar answers "news about our stack", schedule answers "schedule background checks".
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
- The shared rulebooks were filled by hand at init: `stackfoundry render-rulebook <name>` now fills them from the
  profile (test paths, pin and lock files, benchmark folders, the docs root), dropping globs another one covers.
- `render-rule` wrote a description YAML would cut (`: `, ` #`) unquoted for Claude Code and Cursor.
- `survey` crashed on a `package.json` or `composer.json` whose top level is not an object; absurdly nested JSON is
  now "could not run" (exit 2), not a traceback. The survey lists repo extensions and materialized agents, and init
  leaves them alone.
- `volatile-facts --exclude` matched only paths relative to the scanned folder, so the verifier's
  `rules/<layer>-*.md` excludes did nothing when it scanned the repo root.
- Init: links in the instruction block are relative to its file, JSON is written with the `Write` tool, paid or
  manual checks never become `tests` or gates, and `--template` paths are plugin-relative. The researcher greps its
  pack for HTML entities before reporting. Templates `instructions-block` and `code-writer-skill` move to version 3
  (the block says how to customize a skill; code-writer paths are written from the repo root).
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
