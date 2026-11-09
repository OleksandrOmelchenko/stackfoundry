---
name: customize
description: Change what a stackfoundry skill or agent does in this repo without losing it on upgrade — add a step, a rule or a category, or replace it outright. Use for "change how bug-hunt works", "add a step to review-changes".
argument-hint: "[skill or agent] [the change in your words]"
---

# Customize

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

A team wants a plugin skill or agent to work differently in its repo. Editing the installed plugin is lost on the next
update, and a same-named copy in the repo's skills folder does not replace a plugin skill. This skill writes the change
as a repo extension instead: a file under `.stackfoundry/extensions/` that the plugin reads on every run and that
upgrades never overwrite. Read `${CLAUDE_PLUGIN_ROOT}/reference/extensions.md` first; it is the format and the fixed
contract.

## 1. What to change

- The skill or agent: from the argument, or ask (`walkthrough`'s groups, paged three plus **More…**). An agent is
  named by its role (`bug-hunter`); when the change is for one target only, note the target from `targets.json`.
- Read the plugin's file (`${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md` or `agents/<name>.md`) and its current
  extension, if any (`stackfoundry extensions list --json`).
- The change, in the user's words. Ask until it is concrete enough to write: what should happen, at which step, for
  which target.

## 2. Where it belongs

Some changes are not extensions; say so and route them instead:

| The change | Goes to |
|---|---|
| a fact about the code (a path, a harness, a trap) | `.stackfoundry/targets/<target>.md` (Emphasis, Traps) |
| a rule about one technology | the pack's `repoConvention` (`research-stack` keeps it) |
| a reviewer a path or pattern should call in | `targets.json` → `specialists` |
| a deeply tuned agent for one target | `materialize` |
| something new, not a change to a plugin skill | a skill of the repo's own (`skill-agent-author`) |
| a change to the fixed contract | not possible in a repo: suggest an issue on the plugin |

Otherwise it is an extension.

## 3. Extend or replace

Ask (header `How`):

- **Add to it** (Recommended): an `extend` file with anchored sections. The plugin's own improvements keep arriving.
- **Replace it**: a full copy the team edits freely; upgrades three-way merge the plugin's later changes into it.
  Recommend it only when more than about half of the steps change.

## 4. Draft

- `extend`: draft the sections against the plugin file's current headings: `## Rules` for what applies throughout,
  `## Before:` / `## After:` / `## Replace:` a heading (without its number) for a step, `## Target: <name>` for one
  target. Keep each section to what the user asked; never restate the plugin's text.
- `replace`: `stackfoundry extensions new skill|agent <name> --replace` writes the copy and its base; then draft the
  edits to it.
- Check the draft against the fixed contract (confirmations, guards, git policy, brief fields, report and tracker
  shape, severity and verdict words). A draft that touches it is changed or dropped, and you say why.
- Show the full file (or the diff, for `replace`) and ask to write it.

## 5. Write and check

- New `extend` file: `stackfoundry extensions new skill|agent <name>`, then write the drafted sections into it. An
  existing one: edit only its sections.
- `stackfoundry extensions check`; fix every error it reports for this file.
- Never touch the plugin's files, another extension, or anything outside `.stackfoundry/extensions/`.

## 6. Explain

- What changed and when it applies: "from the next run of `<name>`, in every assistant that reads this repo".
- Upgrades keep it: an `extend` file is re-checked against renamed headings, a `replace` copy is merged with the
  plugin's changes (`/stackfoundry:upgrade`).
- Undo: delete the file; for a replacement, also `stackfoundry extensions forget <file>`.
- No git writes: the user commits the file with the rest of the repo.

## Boundaries

- Writes only `.stackfoundry/extensions/` (the extension and, for a replacement, its base). Never the plugin, the
  profile or another skill.
- Never weakens the fixed contract, a guard or a confirmation, whatever the request.

## Tooling

- `Read`/`Grep` the plugin file, `reference/extensions.md` and the profile; `Write`/`Edit` the extension file.
- `Bash` for `stackfoundry extensions list|new|check|forget`.
- `AskUserQuestion` for the skill, the mode and the go-ahead to write.
