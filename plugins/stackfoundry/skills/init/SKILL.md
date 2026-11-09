---
name: init
description: Set up stackfoundry in this repo — survey it, agree the target map, research each technology from current sources, and write grounded rulebooks, target profiles, code-writer skills, trackers and guards.
argument-hint: "[--new] [--targets a,b] [answers for a non-interactive run]"
disable-model-invocation: true
---

# Init

Turns a repository into one stackfoundry can work in. It studies the repo, agrees a **target map** with the user
(every deployable or testable unit and its stack of layers, `${CLAUDE_PLUGIN_ROOT}/reference/layers.md`),
researches every technology in that map from current official sources, and writes the facts every stackfoundry skill
and agent reads. It **never overwrites** existing `.claude/` content or docs: it proposes a merge and asks.

## 0. Preconditions

- A git repository, and `stackfoundry --help` works (Python ≥ 3.11). If not, say what is missing and stop.
- `.claude/stackfoundry/targets.json` already exists → this is not a first run: offer `/stackfoundry:sync` (repo
  changed) or `/stackfoundry:upgrade` (plugin changed) and stop unless the user asks to start over.
- `--new`, or a survey with no manifests and no source: the **interview-first** path (step 2b).
- **Can this session write under `.claude/`?** Claude Code protects that folder: every write there is prompted
  (interactive), routed to a classifier (`auto` mode) or allowed only in `bypassPermissions` mode; allow rules such as
  `Edit(.claude/**)` do not change that. Check now, before any research is spent: write
  `.claude/stackfoundry/.write-probe` and delete it. If it is refused, stop here and say how to rerun (Tooling).
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
   regenerated, commands that must never run (direct database writes, deploys), the docs root (the plugin setting
   `${user_config.docsRoot}`, else `docs`, unless the repo already keeps docs elsewhere), the plan categories, the
   time zone for report dates.
4. Roles to enable per target (default: all), and how to treat existing `.claude/` content (keep side by side
   recommended).

**2b. Interview-first** (an empty or new repo): ask what is being built: the targets, the language and app model of
each, the test framework, the CI. The answers replace the survey; continue at step 3. Say that gates and harnesses
come later (`/stackfoundry:scaffold-test-harness` once code exists).

## 3. Research

Collect the unique packs across all targets. Dispatch one `stackfoundry:stack-researcher` per pack **in one
message** (batches of about six when there are many). Each brief carries `pack:`, `versions:` (where each is pinned),
`evidence:` (the targets and files using it), `exposure:` and `stakes:` of those targets, and
`output: .stackfoundry-staging/packs/<pack-id>/pack.json`, the one file the researcher writes. The staging folder is
outside the protected `.claude/`, so research is saved even if a later write is refused; step 4 moves each checked
pack into `.claude/stackfoundry/packs/` and deletes the staging folder. Follow
`${CLAUDE_PLUGIN_ROOT}/reference/pack-research.md`. When the researchers finish:

- `stackfoundry pack check <output>` for each pack (researchers have no shell, so the check is yours); send errors back to the same researcher (`SendMessage` when the
  host has it, else a new dispatch with the file and the errors), never patch the facts yourself;
- read each pack; reject a rule with no source or no grounding, and say so;
- collect the questions and conflicts (docs vs repo convention) into one `AskUserQuestion` round;
- list every "not reached" item for the report.

## 4. Write (one confirmation first)

List every file to be written, marking each **new** or **merge** (an existing file of the same name), and ask once.
Then write:

| File | From | Recorded with `--template` |
|---|---|---|
| `.claude/stackfoundry/profile.md` | `reference/templates/profile.md` + the interview | `reference/templates/profile.md` |
| `.claude/stackfoundry/targets.json`, `ecosystems.json`, `guards.json` | the agreed map; schemas in `reference/schemas/` | `profile` |
| `.claude/stackfoundry/packs/<pack-id>/pack.json` | moved from `.stackfoundry-staging/` (step 3), then the staging folder is deleted | `research` |
| `.claude/stackfoundry/targets/<target>.md` | `reference/templates/target.md` | that template |
| `.claude/rules/<pack-id>.md` | `stackfoundry pack render <pack.json> --out <rule>`, never by hand | `research` |
| `.claude/rules/testing.md`, `dependency-bumps.md`, `documentation.md` (+ `benchmarking.md` when a benchmark harness exists) | `reference/rulebooks/`, placeholders filled from the profile | that rulebook |
| `.claude/skills/<app-model>-code-writer/SKILL.md` per app model (bare id: `app-model-wpf` → `wpf`) | `reference/templates/code-writer-skill.md` | that template |
| under the docs root, only where missing: `bug-reports/README.md`, `test-designs/README.md`, `plans/README.md`, `plans/_template.md`, `plans/deferred-upgrades.md`, `specifications/README.md`, `security/README.md`, and the reports README in `dependency-reports/`, `radar/` (plus `radar/decisions.md`), `performance-reports/` and `reports/` | `reference/trackers/` (strip each template's own frontmatter) | that tracker |
| the stackfoundry block in `CLAUDE.md` | `reference/templates/claude-md-block.md`, between its markers | that template (the block alone is hashed) |
| `.claude/settings.json`: `extraKnownMarketplaces.stackfoundry` (GitHub `OleksandrOmelchenko/stackfoundry`) and `enabledPlugins["stackfoundry@stackfoundry"]` | merged into the existing JSON | `profile` |

- **Which `CLAUDE.md`**: the root `CLAUDE.md` when it exists, else `.claude/CLAUDE.md` when that exists, else create
  the root one.
- **A repo that is itself the stackfoundry marketplace** (its `.claude-plugin/marketplace.json` lists `stackfoundry`):
  skip the `settings.json` entries; contributors run the working tree with `claude --plugin-dir plugins/stackfoundry`.
- A name collision with an existing rule, skill or doc: write `stackfoundry-<name>` beside it and list it for the
  user to merge, never replace.
- Every generated file is grounded: a placeholder the repo cannot fill is left out, never invented.
- Check as you write: `stackfoundry guard --check` right after `guards.json` (an invalid file is silently ignored
  by the hook), `stackfoundry change-targets --files <one file per target>` right after `targets.json` (it loads and
  validates it), and `stackfoundry verify-plumbing .` right after the code-writer skills (description caps).
- Record every file: `stackfoundry manifest record <files> --template <id from the table>`.

## 5. Prove

- **Gates**: ask once, then run each target's gate commands, respecting its preconditions (never stop a service you
  did not start; ask). Long suites run in the background. Mark each command proven or failed in the target
  profile; a failing gate stays in the profile, marked, and goes in the report.
- `stackfoundry verify-plumbing .` (the repo's `.claude/`), `stackfoundry globs-check` (every rulebook glob matches a
  file), and `/stackfoundry:skill-agent-verifier` for the load probe: every generated rulebook loads when a matching
  file is read.
- `stackfoundry change-targets --files <one source file per target>`: each maps to its own target.
- `stackfoundry guard --check`, then a probe: pipe a sample event into `stackfoundry guard` with
  `CLAUDE_PROJECT_DIR` set. With `generated` globs, an `Edit` of a matching file must be denied; with none, a
  `git commit` must get the `git.writes` decision.

## 6. Report

The target map, the files written (new vs merged), gates proven and failed, research not reached, open questions,
and next steps: `/stackfoundry:bug-hunt <target>`, `/stackfoundry:design-tests <target>`,
`/stackfoundry:threat-model <target>` for public targets, `/stackfoundry:schedule`. Remind that each collaborator
runs `/plugin install stackfoundry@stackfoundry` once (not for the marketplace repo itself). **Do not commit**: say
what is ready to commit.

## Boundaries

- Never edits product code, tests, CI or existing rules; never runs a deploy, a migration or a database write.
- Never fills a fact from memory: research cites, the repo grounds, the user decides.
- Never hand-renders a rulebook or hand-copies a pack out of chat: the researcher writes the pack, the CLI renders.

## Tooling
- `Agent` with `subagent_type: "stackfoundry:surveyor"`, then `"stackfoundry:stack-researcher"` (one per pack, one
  message).
- `AskUserQuestion` for the interview rounds and the one write confirmation.
- `Bash` for `stackfoundry survey|pack|manifest|verify-plumbing|globs-check|change-targets|guard` and the gate
  commands (`run_in_background` for long suites). `Read`/`Write`/`Edit` for the files.
- `Skill` → `stackfoundry:skill-agent-verifier` for the load probe.
- Non-interactive runs: `.claude/` is a protected path, and neither `acceptEdits` nor an allow rule covers it.
  Use `--permission-mode auto` (a classifier reviews each protected write), or `bypassPermissions` only in an
  isolated, disposable clone. Interactive sessions simply prompt.
