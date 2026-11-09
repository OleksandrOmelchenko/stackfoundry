---
name: implement-plan
description: Build a feature plan from the docs plans backlog, then retire it — delete the plan, record a living spec, sync affected instructions. Use when asked to build or execute a backlog plan.
argument-hint: "[plan slug]"
---

# Implement a plan, then retire it

> **Portable form.** `stackfoundry <subcommand>` here means
> `sh "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.sh" <subcommand>` (Windows without `sh`:
> `pwsh -NoProfile -File "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.ps1" <subcommand>`).
> If `${CLAUDE_PLUGIN_ROOT}` is not filled in, it is the folder two levels above this skill's folder; give it to
> every agent you dispatch as `pluginRoot:` in the brief.
> Tool names are Claude Code's; in another assistant use its equivalent
> (`${CLAUDE_PLUGIN_ROOT}/reference/clients.md`).

Takes a plan from `<docsRoot>/plans/` (`targets.json` → `docsRoot`, default `docs`), builds it the repo's way, and
once it is built and verified **retires** it in the same change: the plan is deleted, a living spec records what
was built, and every instruction the change made untrue is synced. The lifecycle is in
`.claude/rules/documentation.md` (*Plans, specifications and the backlog*).

For a change that matters, `/stackfoundry:elaborate-plan` wraps this with a planned test design and a quality
sweep; the retirement below still applies.

## Procedure

1. **Select.** The named `<docsRoot>/plans/<slug>.md`, or list with `stackfoundry backlog --section plans` and
   confirm which one.
2. **Prepare.**
   - Read the plan in full. Map its Affected areas to targets (`stackfoundry change-targets --files <paths>`).
   - A planned change carries its test list before code exists (`.claude/rules/testing.md` §4). When the plan has
     none, design it first with `/stackfoundry:design-tests <target> --spec <plan>`.
   - Read the conventions through `/stackfoundry:write-code`, which routes each target to its code writer and
     rulebooks.
3. **Implement and verify.** Build it part by part. Verify by the plan's **Verification** section and each touched
   target's gate (`targets.json` → `gate`, or `/stackfoundry:run-tests`). Honour `gate.preconditions` and ask
   before stopping a process you did not start. **Do not retire until verification passes.**
4. **Retire** (only after verification passes).
   - `Grep` the slug across the docs root and repoint every link to the plan at the new spec.
   - **Delete** `<docsRoot>/plans/<slug>.md`.
   - **Write the spec** `<docsRoot>/specifications/<slug>.md` in the shape `<docsRoot>/specifications/README.md`
     describes (template: `${CLAUDE_PLUGIN_ROOT}/reference/trackers/specifications-README.md`): the plan's
     `**Category:**` carried to line 3 unchanged, Status, Why, Behaviour, Design by path + symbol, Verification
     (what was exercised and that the gate was green, no suite totals), Follow-ups (not yet implemented).
   - **Add its index row** to `<docsRoot>/specifications/README.md`.
   - **Sync instructions** the change made untrue: `CLAUDE.md` files (outside the stackfoundry markers), the
     team's `.claude/rules/` files, the target profile (`.stackfoundry/targets/<target>.md`) when paths,
     harness, gate or traps changed, and any skill or agent whose behaviour changed. A new project or app model
     means `targets.json` is behind: suggest `/stackfoundry:sync` rather than hand-editing the target map.
5. **Confirm the retirement** with the `plan-sync-reviewer` agent: plan deleted, spec and index row present,
   instructions synced. Fix what it reports.
6. **Report**: what was built, the gate results, the deleted plan, the new spec, every instruction file touched.

## Boundaries

- Never deletes a plan whose verification has not passed; a partly built plan is re-scoped, as
  `/stackfoundry:retire-plan` describes.
- Never flips a bug-report marker (`/stackfoundry:fix-verify` owns them). Never hand-edits generated files.
- No git writes: the finished change is left in the tree and the reply says what is ready to commit.

## Tooling

- `Bash`: `stackfoundry backlog`, `stackfoundry change-targets`, the gate commands, deleting the plan file.
- `Skill` → `stackfoundry:write-code`, `stackfoundry:design-tests`, `stackfoundry:run-tests`.
- `Write`/`Edit` the spec, the README row and the synced instructions.
- `Agent` with `subagent_type: "stackfoundry:plan-sync-reviewer"`, brief: `scope:` the plan slug and the change
  (the uncommitted tree, or `diff: <base>...HEAD`), `mode: review`, `concurrency: read-only, do not build`.
