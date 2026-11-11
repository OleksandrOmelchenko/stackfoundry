---
name: sync
description: Re-survey the repo and update the stackfoundry profile — new or removed projects, frameworks and tools, pinned majors that moved, new generated folders. Shows one diff, asks once, applies. Use for "resync stackfoundry" or "I added a project".
argument-hint: "[--targets a,b]"
---

# Sync

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

Keeps `.stackfoundry/` true as the repo changes. `init` builds the profile once; this skill finds where it
drifted and proposes the smallest change that fixes it. Plugin template changes are `/stackfoundry:upgrade`'s job.

## 1. Compare

Run `stackfoundry survey` (`--pretty` is not needed) and compare with `targets.json`, `ecosystems.json`,
`guards.json` and the packs:

| Drift | Evidence | Proposed change |
|---|---|---|
| A unit no target's `paths` covers | survey unit outside every target | a new target, or add its paths to an existing one (ask which) |
| A target's paths match nothing | glob with no files | remove the target or fix its paths |
| A hint for a pack no target lists | a dependency or config-file hint | add the pack to the target and research it |
| A pack no target uses any more | no file or dependency left | drop it from `packs`; keep its files until the user deletes them |
| A pinned major moved past the researched one | manifest vs `pack.json` `versions` | `/stackfoundry:research-stack <pack> --refresh` |
| A pack older than the refresh window | `researchedAt` vs `stackfoundry config researchRefreshDays` | refresh |
| A new generated folder | survey `generatedDirs` not in `generated` / `guards.json` | add the glob and its regenerate hint |
| A `guards.json` the hook cannot read (its rules are silently off) | `stackfoundry guard --check` reports a problem | fix the file; `/stackfoundry:configure-guards` when a rule is unclear |
| A file no target or rule maps, or one a no-target rule hides | `stackfoundry change-targets --all`: **Unmapped**, **Shadowed** | a rule, a target path, or an anchored glob (`/*.md`) |
| A gate command whose script or project vanished | the command's target file is gone | fix or mark unproven |
| A new manifest or lock file | survey manifests vs `ecosystems.json` pins | add it to an ecosystem |
| An assistant in use that `config.json` does not list, or one listed that is gone | survey `assistants.detected` vs `stackfoundry config clients` | add or drop it in `clients`, then write or remove its files (below) |
| An assistant's copy missing or differing from its source | `stackfoundry outputs` vs the files; `stackfoundry render-rule <canonical> --client <assistant>` vs the copy | re-render it (an edited copy: ask first) |
| The product grew past its profile | a new unit or dependency that names a business capability `product.json` does not reflect (payments, a mobile app, a new market's locale or currency), or no `product.json` at all | propose the edit to `product.json` (or a draft, as the surveyor writes it); a changed `category`, `audiences` or `markets` makes the domain brief stale for `/stackfoundry:whats-next` |

Confirm each candidate against the code before proposing it: a hint is evidence, not a decision.

## 2. Ask once

Present the drift table and ask with `AskUserQuestion` (a multi-select of the changes, plus a question for each
ambiguous app model or new target's exposure and stakes).

## 3. Apply

- Profile JSON and target profiles: edit in place (show the diff).
- New and refreshed packs: `/stackfoundry:research-stack` for each, dispatched in one message when there are several.
- New targets: their target profile and gate, as `/stackfoundry:init` steps 4–5 do for one target (prove the gate
  once, with permission).
- A changed `clients` list: for each assistant added, write what `stackfoundry outputs` lists for it (rulebook
  copies with `render-rule --write`, its instruction-file block with `render-block --write`, code-writer skills,
  materialized agents with `render-agent --write`, which refuses an agent setting a host-privileged key: show it and
  ask); for one removed, list its generated files (`stackfoundry manifest list`) and ask before deleting any.
- `stackfoundry manifest record` for every generated file written.

## 4. Report

What changed, what was declined, gates proven, packs still stale. Do not commit.

## Tooling
- `Bash` for `stackfoundry survey|config|outputs|render-rule|render-agent|render-block|manifest|change-targets` and gates; `Read`/`Edit`/`Write` for the profile.
- `Agent` with `subagent_type: "stackfoundry:surveyor"` when the drift is large enough to need a fresh target map.
- `Skill` → `stackfoundry:research-stack` per pack; `AskUserQuestion` once.
