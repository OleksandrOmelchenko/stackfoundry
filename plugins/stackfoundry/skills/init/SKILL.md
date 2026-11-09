---
name: init
description: Set up stackfoundry in this repo — survey it, agree the target map, research each technology from current sources, write grounded rulebooks, profiles, code-writer skills, trackers and guards. Only when asked. Use for "set up stackfoundry".
argument-hint: "[--new] [--targets a,b] [answers for a non-interactive run]"
---

# Init

> **Portable form.** `stackfoundry <subcommand>` here means
> `sh "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.sh" <subcommand>` (Windows without `sh`:
> `pwsh -NoProfile -File "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.ps1" <subcommand>`).
> If `${CLAUDE_PLUGIN_ROOT}` is not filled in, it is the folder two levels above this skill's folder; give it to
> every agent you dispatch as `pluginRoot:` in the brief.
> Tool names are Claude Code's; in another assistant use its equivalent
> (`${CLAUDE_PLUGIN_ROOT}/reference/clients.md`).
> **Repo extensions.** Before step 1, Read `.stackfoundry/extensions/skills/<this skill's name>.md` in the repo
> if it exists. `mode: replace`: follow its body instead of this file (unless you already are). Otherwise apply
> its sections at the headings they name, and its `## Target:` sections only for that target.
> Its `## Rules` win where they conflict with this file, never over the fixed contract
> (`${CLAUDE_PLUGIN_ROOT}/reference/extensions.md`).

Turns a repository into one stackfoundry can work in. It studies the repo, agrees a **target map** with the user
(every deployable or testable unit and its stack of layers, `${CLAUDE_PLUGIN_ROOT}/reference/layers.md`),
researches every technology in that map from current official sources, and writes the facts every stackfoundry skill
and agent reads. It **never overwrites** existing `.claude/` content or docs: it proposes a merge and asks.

## 0. Preconditions

- A git repository, and `stackfoundry --help` works (Python ≥ 3.11). If not, say what is missing and stop.
- `.stackfoundry/targets.json` already exists → this is not a first run: offer `/stackfoundry:sync` (repo
  changed) or `/stackfoundry:upgrade` (plugin changed) and stop unless the user asks to start over.
- `--new`, or a survey with no manifests and no source: the **interview-first** path (step 2b).
- **Can this session write under `.claude/`?** (Claude Code only, and only when it is one of the repo's clients.)
  Claude Code protects that folder: every write there is prompted (interactive), routed to a classifier (`auto`
  mode) or allowed only in `bypassPermissions` mode; allow rules such as `Edit(.claude/**)` do not change that. The
  facts in `.stackfoundry/` are not affected. Check now, before any research is spent: write
  `.claude/.stackfoundry-write-probe` with the `Write` tool (a shell write is not checked the same way, so it proves
  nothing) and delete it. If it is refused, stop here and say how to rerun (Tooling).
- **Non-interactive run** (`claude -p`, a scheduled task, CI): nobody answers questions. Take answers from the
  arguments; where none is given, choose the option this skill recommends (or the most conservative one) and list
  every such choice under "Decisions made without the user" in the report. Never route around a refused write.

## 1. Survey

Dispatch `stackfoundry:surveyor` with the repo root. It runs `stackfoundry survey`, confirms each hint against the
code and returns a draft target map, ecosystems, guards and questions. Read the draft; check anything surprising
yourself (a unit with no app model, an app model the survey only guessed, a test project with no target).

- Units the survey marks `"fixture": true` (under `fixtures/`, `testdata/`, `samples/`…) are test data or examples,
  never targets, and the profile says why (so no hunter "fixes" them). When tests consume them, map the fixture
  folder through a `rules` entry to the targets whose tests read it, so a fixture change selects those tests;
  otherwise put it in `ignored`.
- `assistants.detected` (with its evidence) is the starting list of the repo's `clients`; confirm it in step 2.
  `agentsMd` alone proves no assistant: ask which ones read it.
- `looseSources` lists source folders no manifest covers (a CLI run by a launcher, a scripts folder): each is a
  candidate target or part of one; ask when unclear.
- A `claude-plugin` unit is a Claude Code plugin; its packs come from the plugin's own layers (skills, agents,
  hooks), plus the languages of any scripts it ships.

## 2. Agree the target map

Show one table: target · paths · stack (packs by layer) · exposure · stakes · evidence. Then ask, with
`AskUserQuestion` (up to 4 questions per call, the most consequential first, at most three rounds):

1. Targets: confirm, split (two app models in one folder, e.g. a component layer and a server-rendering layer) or
   merge. Show the evidence for each split.
2. Ambiguous app models and the exposure and stakes of each target (who can reach it; money, personal data, auth,
   data integrity).
3. Working agreements: the git-write policy (`ask` recommended), the generated folders and how each is
   regenerated, commands that must never run (direct database writes, deploys), the docs root (`docs` unless the
   repo already keeps docs elsewhere), the plan categories, the time zone for report dates, and the assistants the
   team uses (`clients`: claude-code, codex, copilot, cursor, gemini; `${CLAUDE_PLUGIN_ROOT}/reference/clients.md`).
4. Roles to enable per target (default: all), and how to treat existing `.claude/` content (keep side by side
   recommended).

**2b. Interview-first** (an empty or new repo): ask what is being built: the targets, the language and app model of
each, the test framework, the CI. The answers replace the survey; continue at step 3. Say that gates and harnesses
come later (`/stackfoundry:scaffold-test-harness` once code exists).

## 3. Research

Collect the unique packs across all targets. Dispatch one `stackfoundry:stack-researcher` per pack **in one
message** (batches of about six when there are many). Each brief carries `pack:`, `versions:` (where each is pinned),
`evidence:` (the targets and files using it), `exposure:` and `stakes:` of those targets, and
`output: .stackfoundry/packs/<pack-id>/pack.json`, the one file the researcher writes. Follow
`${CLAUDE_PLUGIN_ROOT}/reference/pack-research.md`. When the researchers finish:

- `stackfoundry pack check <output>` for each pack (researchers have no shell, so the check is yours); send errors back to the same researcher (`SendMessage` when the
  host has it, else a new dispatch with the file and the errors), never patch the facts yourself;
- read each pack; reject a rule with no source or no grounding, and say so;
- collect the questions and conflicts (docs vs repo convention) into one `AskUserQuestion` round;
- list every "not reached" item for the report.

## 4. Write (one confirmation first)

`.stackfoundry/config.json` names the repo's assistants; `stackfoundry outputs` (after writing it) says where each
kind of file goes for them, so no assistant gets a copy another one already reads. List every file to be written,
marking each **new** or **merge** (an existing file of the same name), and ask once. Then write:

| File | From | Recorded with `--template` |
|---|---|---|
| `.stackfoundry/profile.md` | `reference/templates/profile.md` + the interview | `reference/templates/profile.md` |
| `.stackfoundry/config.json` | the interview: `clients`, `docsRoot` (defaults: `stackfoundry config`) | `profile` |
| `.stackfoundry/targets.json`, `ecosystems.json`, `guards.json` | the agreed map; schemas in `reference/schemas/` | `profile` |
| `.stackfoundry/packs/<pack-id>/pack.json` | written by its researcher (step 3) | `research` |
| `.stackfoundry/targets/<target>.md` | `reference/templates/target.md` | that template |
| `.stackfoundry/rules/<pack-id>.md` | `stackfoundry pack render <pack.json> --out <rule>`, never by hand | `research` |
| `.stackfoundry/rules/testing.md`, `dependency-bumps.md`, `documentation.md` (+ `benchmarking.md` when a benchmark harness exists) | `stackfoundry render-rulebook <name> --write`, after `targets.json` and `ecosystems.json`; never by hand | `reference/rulebooks/<name>.md` |
| each assistant's copy of every rulebook (`outputs` → rules: `.claude/rules/`, `.github/instructions/`, `.cursor/rules/`) | `stackfoundry render-rule .stackfoundry/rules/<id>.md --client <assistant> --write` | as its canonical rulebook |
| `<app-model>-code-writer/SKILL.md` per app model (bare id: `app-model-wpf` → `wpf`), in each `outputs` → skills folder | `reference/templates/code-writer-skill.md` | that template |
| under the docs root, only where missing: `bug-reports/README.md`, `test-designs/README.md`, `plans/README.md`, `plans/_template.md`, `plans/deferred-upgrades.md`, `specifications/README.md`, `security/README.md`, and the reports README in `dependency-reports/`, `radar/` (plus `radar/decisions.md`), `performance-reports/` and `reports/` | `reference/trackers/` (strip each template's own frontmatter) | that tracker |
| the stackfoundry block in each `outputs` → instructions file (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`) | `reference/templates/instructions-block.md`, between its markers | that template (the block alone is hashed) |
| Claude Code only: `.claude/settings.json`: `extraKnownMarketplaces.stackfoundry` (GitHub `OleksandrOmelchenko/stackfoundry`) and `enabledPlugins["stackfoundry@stackfoundry"]` | merged into the existing JSON | `profile` |

- **Which instruction file**: for `CLAUDE.md`, the root one when it exists, else `.claude/CLAUDE.md` when that
  exists, else create the root one; `AGENTS.md` and `GEMINI.md` at the root. For Codex and Gemini, which have no
  path-scoped rules, the block's table is the instruction to read a rulebook before editing a matching file.
- **A repo that is itself the stackfoundry marketplace** (its `.claude-plugin/marketplace.json` lists `stackfoundry`):
  skip the `settings.json` entries; contributors run the working tree with `claude --plugin-dir plugins/stackfoundry`.
- A name collision with an existing rule, skill or doc: write `stackfoundry-<name>` beside it and list it for the
  user to merge, never replace.
- Every generated file is grounded: a placeholder the repo cannot fill is left out, never invented.
- **Links in an instruction block** are relative to the file that holds it: in `.claude/CLAUDE.md` a rulebook is
  `../.stackfoundry/rules/<id>.md`; in a root `CLAUDE.md`, `AGENTS.md` or `GEMINI.md`, `.stackfoundry/rules/<id>.md`.
- **Write JSON with the `Write` tool**, never through a shell heredoc or `echo`: the shell can eat backslashes in
  regex patterns (`guards.json`), and `guard --check` then reports a pattern that no longer means what was agreed.
- **A check that costs money or needs a person** (a paid eval suite, a manual smoke test) is never a `tests` entry
  or part of a `gate`: `select-tests` and the gates run those unattended. Name it in the target profile instead, and
  ask-guard its command in `guards.json`.
- **Repo extensions** already in `.stackfoundry/extensions/` (the survey lists them) are the team's: never touch them;
  after writing, run `stackfoundry extensions check` and list each one in the report with what it changes.
- `--template` values are paths relative to the plugin root (`reference/templates/target.md`), or `research` /
  `profile`, exactly as the table gives them.
- Check as you write: `stackfoundry config` right after `config.json`, `stackfoundry guard --check` right after
  `guards.json` (an invalid file is silently ignored by the hook), `stackfoundry change-targets --files <one file per
  target>` right after `targets.json` (it loads and validates it), and `stackfoundry verify-plumbing .` right after
  the code-writer skills (description caps).
- Record every file: `stackfoundry manifest record <files> --template <id from the table>`.

## 5. Prove

- **Gates**: ask once, then run each target's gate commands, respecting its preconditions (never stop a service you
  did not start; ask). Long suites run in the background. Mark each command proven or failed in the target
  profile; a failing gate stays in the profile, marked, and goes in the report.
- `stackfoundry verify-plumbing .` (the repo's skills and agents), `stackfoundry globs-check` (every rulebook glob
  matches a file), and, when the session is Claude Code, `/stackfoundry:skill-agent-verifier` for the load probe:
  every generated rulebook loads when a matching file is read.
- `stackfoundry change-targets --files <one source file per target>`: each maps to its own target.
- `stackfoundry guard --check`, then a probe: write a sample event to a file with the `Write` tool, then run
  `stackfoundry guard < <file>` with `CLAUDE_PROJECT_DIR` set. Never put the event in the command line (a heredoc or
  an `echo`): the live guard reads the whole command and refuses the probe itself. With `generated` globs, an `Edit` of a matching file must be denied; with none, a
  `git commit` must get the `git.writes` decision. For each other assistant in `clients`, say what its guard can do
  there (`${CLAUDE_PLUGIN_ROOT}/reference/clients.md`, *The guard in each assistant*).

## 6. Report

The target map, the files written (new vs merged), gates proven and failed, research not reached, open questions,
and next steps: `/stackfoundry:bug-hunt <target>`, `/stackfoundry:design-tests <target>`,
`/stackfoundry:threat-model <target>` for public targets, `/stackfoundry:schedule`. Remind that each collaborator
installs the plugin once in their assistant (the README's install table; not for the marketplace repo itself). **Do not commit**: say
what is ready to commit.

## Boundaries

- Never edits product code, tests, CI or existing rules; never runs a deploy, a migration or a database write.
- Never fills a fact from memory: research cites, the repo grounds, the user decides.
- Never hand-renders a rulebook or hand-copies a pack out of chat: the researcher writes the pack, the CLI renders.

## Tooling
- `Agent` with `subagent_type: "stackfoundry:surveyor"`, then `"stackfoundry:stack-researcher"` (one per pack, one
  message).
- `AskUserQuestion` for the interview rounds and the one write confirmation.
- `Bash` for `stackfoundry survey|config|outputs|pack|render-rule|render-rulebook|manifest|extensions|verify-plumbing|globs-check|change-targets|guard` and the gate
  commands (`run_in_background` for long suites). `Read`/`Write`/`Edit` for the files.
- `Skill` → `stackfoundry:skill-agent-verifier` for the load probe.
- Non-interactive runs: `.claude/` is a protected path, and neither `acceptEdits` nor an allow rule covers it.
  Use `--permission-mode auto` (a classifier reviews each protected write), or `bypassPermissions` only in an
  isolated, disposable clone. Interactive sessions simply prompt.
