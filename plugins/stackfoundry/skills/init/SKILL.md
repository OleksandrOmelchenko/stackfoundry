---
name: init
description: Set up stackfoundry in this repo — survey it, agree the target map, research each technology from current sources, and write grounded rulebooks, target profiles, code-writer skills, trackers and guards.
argument-hint: "[--new] [--targets a,b]"
disable-model-invocation: true
---

# Init

Turns a repository into one stackfoundry can work in. It studies the repo, agrees a **target map** with the user
(every deployable or testable unit and its stack of layers, `${CLAUDE_PLUGIN_ROOT}/reference/layers.md`),
researches every technology in that map from current official sources, and writes the facts every stackfoundry skill
and agent reads. It **never overwrites** existing `.claude/` content or docs: it proposes a merge and asks.

## 0. Preconditions

- A git repository, and `stackfoundry --help` works (Python ≥ 3.10). If not, say what is missing and stop.
- `.claude/stackfoundry/targets.json` already exists → this is not a first run: offer `/stackfoundry:sync` (repo
  changed) or `/stackfoundry:upgrade` (plugin changed) and stop unless the user asks to start over.
- `--new`, or a survey with no manifests and no source: the **interview-first** path (step 2b).

## 1. Survey

Dispatch `stackfoundry:surveyor` with the repo root. It runs `stackfoundry survey`, confirms each hint against the
code and returns a draft target map, ecosystems, guards and questions. Read the draft; check anything surprising
yourself (a unit with no app model, an app model the survey only guessed, a test project with no target).

## 2. Agree the target map

Show one table: target · paths · stack (packs by layer) · exposure · stakes · evidence. Then ask, with
`AskUserQuestion` (up to 4 questions per call, the most consequential first, at most three rounds):

1. Targets: confirm, split (two app models in one folder, e.g. a component layer and a server-rendering layer) or
   merge. Show the evidence for each split.
2. Ambiguous app models and the exposure and stakes of each target (who can reach it; money, personal data, auth,
   data integrity).
3. Working agreements: the git-write policy (`ask` recommended), the generated folders and how each is
   regenerated, commands that must never run (direct database writes, deploys), the docs root, the plan categories,
   the time zone for report dates.
4. Roles to enable per target (default: all), and how to treat existing `.claude/` content (keep side by side
   recommended).

**2b. Interview-first** (an empty or new repo): ask what is being built: the targets, the language and app model of
each, the test framework, the CI. The answers replace the survey; continue at step 3. Say that gates and harnesses
come later (`/stackfoundry:scaffold-test-harness` once code exists).

## 3. Research

Collect the unique packs across all targets. Dispatch one `stackfoundry:stack-researcher` per pack **in one
message** (batches of about six when there are many), each with: the pack id and layer, the versions in use and where
they are pinned, the repo evidence (files using it), and the risk profile of the targets that use it. Follow
`${CLAUDE_PLUGIN_ROOT}/reference/pack-research.md`. When packs come back:

- read each one; reject a rule with no source or no grounding, and say so;
- collect the questions and conflicts (docs vs repo convention) into one `AskUserQuestion` round;
- list every "not reached" item for the report.

## 4. Write (one confirmation first)

List every file to be written, marking each **new** or **merge** (an existing file of the same name), and ask once.
Then write:

| File | From |
|---|---|
| `.claude/stackfoundry/profile.md` | `reference/templates/profile.md` + the interview |
| `.claude/stackfoundry/targets.json`, `ecosystems.json`, `guards.json` | the agreed map; schemas in `reference/schemas/` |
| `.claude/stackfoundry/packs/<pack-id>/pack.json` | each researched pack |
| `.claude/stackfoundry/targets/<target>.md` | `reference/templates/target.md` |
| `.claude/rules/<pack-id>.md` | `reference/templates/pack-rulebook.md`, `paths:` from the pack's `rulebookPaths` |
| `.claude/rules/testing.md`, `dependency-bumps.md`, `documentation.md` (+ `benchmarking.md` when a benchmark harness exists) | `reference/rulebooks/`, placeholders filled from the profile |
| `.claude/skills/<app-model>-code-writer/SKILL.md` per app model | `reference/templates/code-writer-skill.md` |
| tracker READMEs and templates under the docs root, only where missing | `reference/trackers/` |
| the stackfoundry block in the root `CLAUDE.md` | `reference/templates/claude-md-block.md`, between its markers |
| `.claude/settings.json`: `extraKnownMarketplaces.stackfoundry` (GitHub `OleksandrOmelchenko/stackfoundry`) and `enabledPlugins["stackfoundry@stackfoundry"]` | merged into the existing JSON |

- A name collision with an existing rule, skill or doc: write `stackfoundry-<name>` beside it and list it for the
  user to merge, never replace.
- Every generated file is grounded: a placeholder the repo cannot fill is left out, never invented.
- Record every file: `stackfoundry manifest record <files> --template <plugin-relative template>`; packs and pack
  rulebooks with `--template research`.

## 5. Prove

- **Gates**: ask once, then run each target's gate commands, respecting its preconditions (never stop a service you
  did not start; ask). Long suites run in the background. Mark each command proven or failed in the target
  profile; a failing gate stays in the profile, marked, and goes in the report.
- `stackfoundry verify-plumbing .` (the repo's `.claude/`) and `/stackfoundry:skill-agent-verifier` for the load
  probe: every generated rulebook loads when a matching file is read.
- `stackfoundry change-targets --files <one source file per target>`: each maps to its own target.
- The guard: pipe a sample `Edit` event for a generated file into `stackfoundry guard` with `CLAUDE_PROJECT_DIR`
  set; it must deny.

## 6. Report

The target map, the files written (new vs merged), gates proven and failed, research not reached, open questions,
and next steps: `/stackfoundry:bug-hunt <target>`, `/stackfoundry:design-tests <target>`,
`/stackfoundry:threat-model <target>` for public targets, `/stackfoundry:schedule`. Remind that each collaborator
runs `/plugin install stackfoundry@stackfoundry` once. **Do not commit**: say what is ready to commit.

## Boundaries

- Never edits product code, tests, CI or existing rules; never runs a deploy, a migration or a database write.
- Never fills a fact from memory: research cites, the repo grounds, the user decides.

## Tooling
- `Agent` with `subagent_type: "stackfoundry:surveyor"`, then `"stackfoundry:stack-researcher"` (one per pack, one
  message).
- `AskUserQuestion` for the interview rounds and the one write confirmation.
- `Bash` for `stackfoundry survey|manifest|verify-plumbing|change-targets|guard` and the gate commands
  (`run_in_background` for long suites). `Read`/`Write`/`Edit` for the files.
- `Skill` → `stackfoundry:skill-agent-verifier` for the load probe.
