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
> **Repo extensions.** Before step 1, Read `.stackfoundry/extensions/skills/<this skill's name>.md` in the repo
> if it exists. `mode: replace`: follow its body instead of this file (unless you already are). Otherwise apply
> its sections at the headings they name, and its `## Target:` sections only for that target.
> Its `## Rules` win where they conflict with this file, never over the fixed contract
> (`${CLAUDE_PLUGIN_ROOT}/reference/extensions.md`).

The user doesn't know the skill names, or doesn't want to. Lead them to the right skill by questions they can click
through, teach them the plain request that starts it next time, and run it only on their yes. Never describe a skill
from memory: its description and `argument-hint` in `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md` are the truth.

Part of the tour is that every skill can be changed for this repo, and the change survives plugin updates
(`${CLAUDE_PLUGIN_ROOT}/reference/extensions.md`): say so wherever a skill is explained, and route "change how X
works" to `customize`.

An argument is a goal in the user's words ("I want fewer flaky tests"): match it against the descriptions and go
straight to step 4 with the best one or two candidates. A goal that is a change to a skill ("make bug-hunt check our
logging") goes to `customize` with that skill.

The tour also shows what can run on its own. The skills in the "Proposed cadence" table of
`${CLAUDE_PLUGIN_ROOT}/skills/schedule/SKILL.md` are unattended: each run writes one dated report under the docs root
and never changes code, so they can run on a timer. Read that table at the start; never list them from memory.

## The groups

Every skill of the plugin is in exactly one row, most-asked first (`verify-plumbing` checks that none is missing):

| Group | Skills |
|---|---|
| Write and test code | `write-code`, `write-tests`, `run-tests`, `design-tests`, `review-tests`, `fix-tests`, `scaffold-test-harness`, `setup-mutation`, `write-benchmarks`, `run-benchmarks` |
| Find and fix problems | `bug-hunt`, `debug`, `fix-ci`, `fix-verify`, `security-review-target`, `threat-model`, `performance-review`, `flaky-watch` |
| Stay current: stack news, updates and scheduled checks | `tech-radar`, `check-updates`, `schedule`, `act-on-radar`, `act-on-updates`, `radar-digest`, `bump`, `bump-all`, `check-formats`, `stackfoundry-radar` |
| Review a change | `review-changes`, `quality-review`, `quality-sweep`, `change-targets`, `prune-comments` |
| Plan what's next | `whats-next`, `backlog`, `plan-feature`, `implement-plan`, `retire-plan`, `elaborate-plan`, `docs-reconciler` |
| Ways of working and git | `with-plan`, `plan-execute`, `implement-only`, `ask-me`, `github-prs`, `cleanup-merged` |
| stackfoundry itself | `init`, `customize`, `sync`, `upgrade`, `research-stack`, `materialize`, `configure-guards`, `skill-agent-author`, `skill-agent-verifier` |

When the repo has skills of its own, they form one more group, **Your repo's skills**, after these.

## 1. State

- `.stackfoundry/targets.json` exists → the repo is set up. Read its target names, and `stackfoundry config --json`
  for the assistants (`clients`).
- Read every skill's `description:` and `argument-hint:` once (`Grep` for `^(description|argument-hint):` in
  `${CLAUDE_PLUGIN_ROOT}/skills/*/SKILL.md`), and the same for the repo's own skills (`.claude/skills/*/SKILL.md`,
  `.agents/skills/*/SKILL.md`).
- `stackfoundry extensions list --json`: which plugin skills and agents this repo already changes, and how (it lists
  nothing on a repo without extensions).

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
  descriptions; "change how X works" goes to `customize` with X; news, "what's new", "keep me posted" or "in the
  background" goes to the Stay-current group, `tech-radar` first; "what next", "roadmap", "what's missing" or
  "what should we build" goes to the Plan-what's-next group, `whats-next` first.
- **Skill**: a second question over the group's skills, paged the same way. Each option's label is the skill name and
  its description is the skill's own trigger phrase (the `Use for …` clause), so the user learns how to ask. A skill
  this repo extends or replaces adds "(changed in this repo)" to its option description.

## 4. Explain and fill in

- Three lines: what the skill does (its description, shortened); the plain request that starts it next time, with
  the slash form in Claude Code (`/stackfoundry:<name> <args>`); and "To change it for this repo, say *customize
  <name>*: the change lives in `.stackfoundry/extensions/` and survives plugin updates."
- When this repo already changes it, say how, naming the file: "this repo extends it:
  `.stackfoundry/extensions/skills/<name>.md` adds a rule and a step after *Verify*" (from the file's sections), or
  "this repo replaces it with its own copy". A repo skill is the repo's own: say so, with no plugin slash form.
- A schedulable skill gets one more line: "It is built to run unattended: say *schedule <name>* and it runs on a
  timer (the cadence `schedule` proposes), writing a dated report under `<docsRoot>/` each time; it never changes
  code." Name its follow-up when it has one (`act-on-radar` after `tech-radar`, `act-on-updates` after
  `check-updates`).
- Arguments from its `argument-hint`, one question each, only the ones that change what runs:
  - `<target>`: the target names from `targets.json` (paged). Never guess one.
  - `diff` / an area / `--base`: **my uncommitted changes**, **a folder or file** (typed in "Other"), **the whole
    target**.
  - Any other required `<argument>`: ask for it in words.
- Then one question (header `Run it?`): **Run it** (Recommended), **Tell me more** (five bullets from its step
  headings, which are also the anchors a change can attach to, then ask again), **Change how it works** (run
  `customize` with this skill), **Pick something else** (back to step 3). "Done" goes through "Other".
  For a schedulable skill: **Run it now** (Recommended), **Schedule it** (run `schedule` with this skill),
  **Change how it works**, **Pick something else**; "Tell me more" goes through "Other".

## 5. Run and loop

- **Run it**: invoke the skill with the filled-in arguments (`Skill` with `stackfoundry:<name>`; elsewhere, run the
  skill by name). It asks its own questions and keeps its own confirmations.
- **Change how it works**: invoke `customize` with the skill's name; it asks what to change and writes nothing
  without a yes.
- **Schedule it**: invoke `schedule` with the skill's name; it shows the cadence and the task, and registers
  nothing without a yes.
- When either finishes, ask once: **Something else** (back to step 3) or **Done**.
- **Done**: list what ran and, for each, the plain request that starts it next time; list any extension written in
  this session with its file and how to undo it (delete the file). When a schedulable skill ran but was not
  scheduled, end with: "Want this on a timer? Say *schedule <name>*.

## Rules

- Nothing runs without the user's yes, and nothing is written by this skill itself.
- No answer to ask (a headless run, or an assistant without a question tool that can't wait): with a goal, give
  step 4's explanation of the best match (including how this repo changes it, if it does) and the options you would
  have offered; without one, print the groups table with each skill's trigger phrase. Then stop; run nothing.
- `AskUserQuestion` conventions: at most four options per question, the recommendation first with "(Recommended)",
  a `header` of 12 characters or fewer, each option's `description` saying what happens, not restating the label.

## Tooling

- `Read` and `Grep` for the profile, the skills' frontmatter and extension files; `Bash` only for
  `stackfoundry config --json` and `stackfoundry extensions list --json`.
- `AskUserQuestion` for every step; in another assistant, ask in chat one question at a time with numbered options
  and wait.
- `Skill` to run the chosen skill.
