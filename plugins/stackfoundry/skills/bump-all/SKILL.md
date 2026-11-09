---
name: bump-all
description: Bump every ecosystem in one sweep — discover all, one table with majors flagged, apply what the user approves in apply order with each ecosystem's gate, record declined majors. Use for "bump everything".
argument-hint: "[ecosystem-id ...] [approve: <item> ...]"
---

# Bump all

> **Portable form.** `stackfoundry <subcommand>` here means
> `sh "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.sh" <subcommand>` (Windows without `sh`:
> `pwsh -NoProfile -File "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.ps1" <subcommand>`).
> If `${CLAUDE_PLUGIN_ROOT}` is not filled in, it is the folder two levels above this skill's folder; give it to
> every agent you dispatch as `pluginRoot:` in the brief.
> Tool names are Claude Code's; in another assistant use its equivalent
> (`${CLAUDE_PLUGIN_ROOT}/reference/clients.md`).

`/stackfoundry:bump <ecosystem-id>` knows one ecosystem's pins, gate and traps. This skill only sequences it over
every ecosystem, keeps the user's decisions in one place and writes down what was deferred. It adds no rule of its
own: they are in `.stackfoundry/rules/dependency-bumps.md`.

## Inputs

- The ecosystems and their **apply order** are `.stackfoundry/ecosystems.json` → `ecosystems`, in file order
  (platforms first, then package managers, generators, CI, infrastructure, formats last). Arguments pick a subset
  by `id`; none means every ecosystem.
- `approve: <item> …` names majors already decided by the caller (`/stackfoundry:act-on-updates` passes it), written
  the way the report writes them. With it, every listed major is approved, every other major is declined, and step
  2 asks nothing.

## Procedure

1. **Discover, read-only.** Reuse the newest `<docsRoot>/dependency-reports/*-dependency-updates.md` when it is
   fresh for these ecosystems (rulebook freshness check); otherwise `Skill` → `stackfoundry:check-updates <ids>`.
2. **Present and ask once.** Patches and minors as one block ("apply all"); **each major separately** with its
   breaking note and the files it touches. Nothing is applied before the answer. A `migrate`-route row is never
   applied here: it becomes a plan through `/stackfoundry:act-on-updates` or `/stackfoundry:plan-feature`.
3. **Apply in order**, one ecosystem at a time: `Skill` → `stackfoundry:bump <id> approve: <approved majors of that
   ecosystem>`. Each run applies, regenerates lock files and runs its gate. **Stop at the first red**: a red in one
   ecosystem is not a reason to start the next. Ask then, and only then, whether to revert that ecosystem's edits
   or fix forward.
4. **Close.**
   - Declined or blocked majors go into `ecosystems.json` → `deferredFile` with their unblock condition (when
     act-on-updates is the caller it records the declined ones, so add only the ones a red gate blocked). Delete
     the row of every deferral this sweep applied.
   - After a platform bump, search the old version string across the `CLAUDE.md` files, `.claude/` and
     `<docsRoot>/` (rulebook § After any platform bump).
   - Report per ecosystem: applied · declined · deferred · gate result · the commit message that would describe
     it. No commit unless the user asks; then one per ecosystem, one major per commit.

## What bites here

- **A sweep is long.** One gate per ecosystem, and integration or server-render suites are slow. Say where the
  sweep is; never summarize ahead of a gate that has not run.
- **Builds and services are shared.** A gate may need something stopped or running (each target's
  `gate.preconditions`). Ask the user before stopping anything you did not start.
- **Do not merge ecosystems into one diff.** The order exists for attribution: when a build goes red after one
  ecosystem, it is that one.
- **Majors are the sweep's output, not its obstacle.** A sweep that applied the patches and surfaced the majors
  with their breaking notes did its job even if no major was taken.

## Tooling

- `Skill` → `stackfoundry:check-updates` for step 1, then `stackfoundry:bump <id>` per ecosystem; never
  re-implement either here.
- `AskUserQuestion` once after discovery (the patch/minor block as one option, a multi-select over majors); a
  second question only on a red gate.
- `Edit` for `deferredFile`. Git writes are the user's.
