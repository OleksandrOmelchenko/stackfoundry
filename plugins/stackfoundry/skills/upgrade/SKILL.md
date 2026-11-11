---
name: upgrade
description: Take a new stackfoundry version's template changes into the files init generated here — replace untouched files, ask about edited ones, skip materialized and deleted ones. Only when asked. Use for "update stackfoundry's files in this repo".
---

# Upgrade

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
> (`${CLAUDE_PLUGIN_ROOT}/reference/extensions.md`). Your report names every extension you applied.

After the plugin updates (`claude plugin update stackfoundry@stackfoundry`, or the other assistant's update), the plugin's skills and agents are new, but the files `init`
generated in this repo still come from the old templates. This skill brings them forward without losing the team's
edits. It relies on `.stackfoundry/manifest.lock.json` (`stackfoundry manifest`).

## 0. Move an old profile

A profile in `.claude/stackfoundry/` (the survey reports `hasLegacyStackfoundryProfile`) moves to `.stackfoundry/`
first, so every assistant can read it: move the folder with its contents unchanged, then rewrite each
`.claude/stackfoundry/` path inside `manifest.lock.json`. The plugin settings that lived in Claude Code's plugin
configuration (`docsRoot`, `researchRefreshDays`, `defaultEffort`) go to `.stackfoundry/config.json` with
`clients: ["claude-code"]` (schema `${CLAUDE_PLUGIN_ROOT}/reference/schemas/config.schema.json`); ask the user for
the values they had set, since the plugin can no longer read them. The rulebooks in `.claude/rules/` that the
manifest records become canonical: copy each to `.stackfoundry/rules/` (same name), keep the `.claude/rules/` file
as Claude Code's copy, and move each manifest entry's record to the canonical file while also recording the copy.
A `materialized` agent in `.claude/agents/` moves the same way to `.stackfoundry/agents/`. Then continue with
step 1.

## 1. Plan

`stackfoundry manifest diff --json` gives, per recorded file: its state (untouched · edited · deleted), whether its
template has a newer version, and the action:

| Action | Meaning |
|---|---|
| `replace` | untouched since generation and the template moved: regenerate and write (a target profile: `render-target --write`, which keeps its prose; an unmarked profile's first migration replaces the body under `## Stack` and `## Gate`, so show its `render-target --diff` in the one confirmation) |
| `three-way merge, ask` | edited by the team and the template moved: show both, the user chooses |
| `leave deleted` | the team deleted it: never recreate |
| `merge via extensions merge (materialized)` | the team owns it; the extensions step merges it with the new generic role |
| `re-research via research-stack` | a researched file; content moves with research, not templates |
| `none` | current |

Also read `${CLAUDE_PLUGIN_ROOT}/CHANGELOG.md` for the versions between the manifest's `pluginVersion` and the
installed one, and list any schema changes (`schemaVersion` of the profile JSON files) that need a migration.

## 2. Ask once

Show the plan grouped by action, with the changelog lines that explain each template change. For every
`three-way merge, ask` file, render the new version and show its diff against the current file; ask per file: take
new · keep mine · merge by hand (you produce the merged text and show it before writing).

## 3. Apply

- Regenerate from the new template with the same inputs (the profile, the target, the pack) and write. The shared
  rulebooks (`reference/rulebooks/`) regenerate with `stackfoundry render-rulebook <name> --write`, then each
  assistant's copy with `render-rule`; never fill their placeholders by hand.
- Schema migration: rewrite the JSON to the new shape, keeping every value; validate with the CLI's checks
  (`stackfoundry change-targets --files <any>` loads and checks `targets.json`).
- `stackfoundry manifest record <files> --template <template>` for every file written from the template (take new,
  or an untouched file replaced), and with `--kind merged` added for every file kept by choice or merged by hand.
  The version and hash move forward either way; `merged` makes the next upgrade ask again instead of replacing
  the team's content.
- Each instruction file's block (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`) is regenerated between its markers only,
  with `stackfoundry render-block --write`, after showing `render-block --diff` (the change and each file's size
  before and after) in the one confirmation; text outside the markers is never touched. It also writes or removes
  `.stackfoundry/rulebooks.md`: record it when written, and `manifest forget` it when removed.

## 4. Repo extensions

The team's changes to plugin skills and agents (`${CLAUDE_PLUGIN_ROOT}/reference/extensions.md`) are never
rewritten by an upgrade; this step makes sure they still fit the new plugin.

1. `stackfoundry extensions check`. For each orphaned anchor (a heading the new version renamed or removed), show the
   section, the nearest current heading the check names and the changelog's "Changed (extension anchors)" line, and
   ask where it goes now (`AskUserQuestion`: the nearest heading, another heading, drop the section). Edit only the
   section heading the user picked.
2. `stackfoundry extensions list --json`: for every `replace` file and materialized agent marked behind the plugin,
   run `stackfoundry extensions merge <file>`.
   - `merged`: report it. For a materialized agent, re-render each assistant's copy
     (`stackfoundry render-agent <file> --client <assistant> --write`) and re-record them in the manifest. A
     refusal names a host-privileged key (`permissionMode`, `hooks`, `mcpServers`, `initialPrompt`, threat model
     T12): show it to the user and ask; never strip it silently.
   - `conflict`: show each conflict hunk from `<file>.merge.md` and ask per hunk: keep the repo's · take the
     plugin's · a merge you write and show. Write the settled text to `<file>.merge.md`, then
     `stackfoundry extensions merge <file> --resolved`.
3. `extend` files: nothing to merge; the plugin's new text reaches the team through them on the next run.
4. `stackfoundry extensions check` again; it must pass.

## 5. Verify and report

`stackfoundry schedule rules --rewrite` (the scheduled runs' allow rules name the plugin's folder, which moved;
it changes only rules stackfoundry wrote, and does nothing where none were), then `stackfoundry verify-plumbing .`
and `stackfoundry size-check`, then `/stackfoundry:skill-agent-verifier`. Report: replaced, merged, kept, skipped,
the extensions re-anchored or merged, and anything the changelog says needs a manual step. Do not commit.

## Tooling
- `Bash` for `stackfoundry manifest diff|record`, `extensions check|list|merge`, `render-agent`, `render-rulebook`,
  `render-target`, `schedule rules --rewrite`,
  `render-block`, `verify-plumbing`, `size-check`, `change-targets`.
- `Read` the templates through `${CLAUDE_PLUGIN_ROOT}/reference/templates/`, `rulebooks/` and `trackers/`;
  `Write`/`Edit` the files.
- `AskUserQuestion` once (one question per edited file, four per call).
- `Skill` → `stackfoundry:skill-agent-verifier`.
