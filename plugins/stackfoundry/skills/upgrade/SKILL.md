---
name: upgrade
description: Take a new stackfoundry plugin version's template changes into the files init generated here — replace untouched files, ask about edited ones, skip materialized ones, leave deleted ones deleted.
disable-model-invocation: true
---

# Upgrade

After `claude plugin update stackfoundry@stackfoundry`, the plugin's skills and agents are new, but the files `init`
generated in this repo still come from the old templates. This skill brings them forward without losing the team's
edits. It relies on `.claude/stackfoundry/manifest.lock.json` (`stackfoundry manifest`).

## 1. Plan

`stackfoundry manifest diff --json` gives, per recorded file: its state (untouched · edited · deleted), whether its
template has a newer version, and the action:

| Action | Meaning |
|---|---|
| `replace` | untouched since generation and the template moved: regenerate and write |
| `three-way merge, ask` | edited by the team and the template moved: show both, the user chooses |
| `leave deleted` | the team deleted it: never recreate |
| `skip (materialized)` | the team owns it |
| `re-research via research-stack` | a researched file; content moves with research, not templates |
| `none` | current |

Also read `${CLAUDE_PLUGIN_ROOT}/CHANGELOG.md` for the versions between the manifest's `pluginVersion` and the
installed one, and list any schema changes (`schemaVersion` of the profile JSON files) that need a migration.

## 2. Ask once

Show the plan grouped by action, with the changelog lines that explain each template change. For every
`three-way merge, ask` file, render the new version and show its diff against the current file; ask per file: take
new · keep mine · merge by hand (you produce the merged text and show it before writing).

## 3. Apply

- Regenerate from the new template with the same inputs (the profile, the target, the pack) and write.
- Schema migration: rewrite the JSON to the new shape, keeping every value; validate with the CLI's checks
  (`stackfoundry change-targets --files <any>` loads and checks `targets.json`).
- `stackfoundry manifest record <files> --template <template>` for every file written or kept by choice, so the
  manifest's version and hash move forward.
- The `CLAUDE.md` block is regenerated between its markers only.

## 4. Verify and report

`stackfoundry verify-plumbing .`, then `/stackfoundry:skill-agent-verifier`. Report: replaced, merged, kept, skipped,
and anything the changelog says needs a manual step. Do not commit.

## Tooling
- `Bash` for `stackfoundry manifest diff|record`, `verify-plumbing`, `change-targets`.
- `Read` the templates through `${CLAUDE_PLUGIN_ROOT}/reference/templates/`, `rulebooks/` and `trackers/`;
  `Write`/`Edit` the files.
- `AskUserQuestion` once (one question per edited file, four per call).
- `Skill` → `stackfoundry:skill-agent-verifier`.
