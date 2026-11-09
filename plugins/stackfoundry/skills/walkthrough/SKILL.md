---
name: walkthrough
description: Guided tour by questions — finds out what you want to do and whether this repo is set up, explains the matching skill in two lines and runs it with your yes. Use for "walk me through stackfoundry", "where do I start", "what can you do".
argument-hint: "[a goal in your own words]"
---

# Walkthrough

> **Portable form.** `stackfoundry <subcommand>` here means
> `sh "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.sh" <subcommand>` (Windows without `sh`:
> `pwsh -NoProfile -File "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.ps1" <subcommand>`).
> If `${CLAUDE_PLUGIN_ROOT}` is not filled in, it is the folder two levels above this skill's folder; give it to
> every agent you dispatch as `pluginRoot:` in the brief.
> Tool names are Claude Code's; in another assistant use its equivalent
> (`${CLAUDE_PLUGIN_ROOT}/reference/clients.md`).

The user doesn't know the skill names, or doesn't want to. Lead them to the right skill by questions they can click
through, teach them the plain request that starts it next time, and run it only on their yes. Never describe a skill
from memory: its description and `argument-hint` in `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md` are the truth.

An argument is a goal in the user's words ("I want fewer flaky tests"): match it against the descriptions and go
straight to step 4 with the best one or two candidates.

## The groups

Every skill of the plugin is in exactly one row, most-asked first (`verify-plumbing` checks that none is missing):

| Group | Skills |
|---|---|
| Write and test code | `write-code`, `write-tests`, `run-tests`, `design-tests`, `review-tests`, `fix-tests`, `scaffold-test-harness`, `setup-mutation`, `write-benchmarks`, `run-benchmarks` |
| Find and fix problems | `bug-hunt`, `debug`, `fix-ci`, `fix-verify`, `security-review-target`, `threat-model`, `performance-review`, `flaky-watch` |
| Review a change | `review-changes`, `quality-review`, `quality-sweep`, `change-targets`, `prune-comments` |
| Keep dependencies and tools current | `check-updates`, `act-on-updates`, `bump`, `bump-all`, `check-formats`, `tech-radar`, `act-on-radar`, `radar-digest`, `schedule` |
| Plans, docs and backlog | `backlog`, `plan-feature`, `implement-plan`, `retire-plan`, `elaborate-plan`, `docs-reconciler` |
| Ways of working and git | `with-plan`, `plan-execute`, `implement-only`, `ask-me`, `github-prs`, `cleanup-merged` |
| stackfoundry itself | `init`, `sync`, `upgrade`, `research-stack`, `materialize`, `configure-guards`, `stackfoundry-radar`, `skill-agent-author`, `skill-agent-verifier` |

## 1. State

- `.stackfoundry/targets.json` exists → the repo is set up. Read its target names, and `stackfoundry config --json`
  for the assistants (`clients`).
- Read every skill's `description:` and `argument-hint:` once (`Grep` for `^(description|argument-hint):` in
  `${CLAUDE_PLUGIN_ROOT}/skills/*/SKILL.md`).

## 2. Not set up yet

With no profile, ask first (header `Setup`):

- **Set it up now** (Recommended): run `init`.
- **Explain setup first**: say in five bullets what `init` reads, researches and writes (from its description and its
  step headings), then ask again.
- **Show me around**: go to step 3. A skill whose body reads `.stackfoundry/` needs the profile: when the user picks
  one, say so and offer `init` first.
- **Done**.

## 3. Goal and skill

- **Goal**: one question, "What do you want to do?", with the groups as options. A list longer than four is paged:
  three options plus **More…**, in table order. "Other" takes any request in words: match it against the
  descriptions.
- **Skill**: a second question over the group's skills, paged the same way. Each option's label is the skill name and
  its description is the skill's own trigger phrase (the `Use for …` clause), so the user learns how to ask.

## 4. Explain and fill in

- Two lines: what the skill does (its description, shortened), and the plain request that starts it next time,
  with the slash form in Claude Code (`/stackfoundry:<name> <args>`).
- Arguments from its `argument-hint`, one question each, only the ones that change what runs:
  - `<target>`: the target names from `targets.json` (paged). Never guess one.
  - `diff` / an area / `--base`: **my uncommitted changes**, **a folder or file** (typed in "Other"), **the whole
    target**.
  - Any other required `<argument>`: ask for it in words.
- Then one question (header `Run it?`): **Run it** (Recommended), **Tell me more** (five bullets from its step
  headings, then ask again), **Pick something else** (back to step 3), **Done**.

## 5. Run and loop

- **Run it**: invoke the skill with the filled-in arguments (`Skill` with `stackfoundry:<name>`; elsewhere, run the
  skill by name). It asks its own questions and keeps its own confirmations.
- When it finishes, ask once: **Something else** (back to step 3) or **Done**.
- **Done**: list what ran and, for each, the plain request that starts it next time.

## Rules

- Nothing runs without the user's yes, and nothing is written by this skill itself.
- No answer to ask (a headless run, or an assistant without a question tool that can't wait): print the groups table
  with each skill's trigger phrase and stop.
- `AskUserQuestion` conventions: at most four options per question, the recommendation first with "(Recommended)",
  a `header` of 12 characters or fewer, each option's `description` saying what happens, not restating the label.

## Tooling

- `Read` and `Grep` for the profile and the skills' frontmatter; `Bash` only for `stackfoundry config --json`.
- `AskUserQuestion` for every step; in another assistant, ask in chat one question at a time with numbered options
  and wait.
- `Skill` to run the chosen skill.
