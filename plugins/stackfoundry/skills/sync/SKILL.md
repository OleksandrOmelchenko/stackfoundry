---
name: sync
description: Re-survey the repo and update the stackfoundry profile — new or removed projects, new frameworks and tools, pinned majors that moved, new generated folders. Shows one diff, asks once, applies.
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
| A pack older than the refresh window | `researchedAt` vs the plugin's `researchRefreshDays` | refresh |
| A new generated folder | survey `generatedDirs` not in `generated` / `guards.json` | add the glob and its regenerate hint |
| A gate command whose script or project vanished | the command's target file is gone | fix or mark unproven |
| A new manifest or lock file | survey manifests vs `ecosystems.json` pins | add it to an ecosystem |

Confirm each candidate against the code before proposing it: a hint is evidence, not a decision.

## 2. Ask once

Present the drift table and ask with `AskUserQuestion` (a multi-select of the changes, plus a question for each
ambiguous app model or new target's exposure and stakes).

## 3. Apply

- Profile JSON and target profiles: edit in place (show the diff).
- New and refreshed packs: `/stackfoundry:research-stack` for each, dispatched in one message when there are several.
- New targets: their target profile and gate, as `/stackfoundry:init` steps 4–5 do for one target (prove the gate
  once, with permission).
- `stackfoundry manifest record` for every generated file written.

## 4. Report

What changed, what was declined, gates proven, packs still stale. Do not commit.

## Tooling
- `Bash` for `stackfoundry survey|manifest|change-targets` and gates; `Read`/`Edit`/`Write` for the profile.
- `Agent` with `subagent_type: "stackfoundry:surveyor"` when the drift is large enough to need a fresh target map.
- `Skill` → `stackfoundry:research-stack` per pack; `AskUserQuestion` once.
