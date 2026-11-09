---
name: plan-feature
description: Capture a future feature as a standalone plan file in the docs plans backlog, without implementing it. Use to plan or park a feature for later, or add something to the roadmap or backlog.
argument-hint: "<feature idea>"
---

# Plan a feature for later

> **Portable form.** `stackfoundry <subcommand>` here means
> `sh "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.sh" <subcommand>` (Windows without `sh`:
> `pwsh -NoProfile -File "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.ps1" <subcommand>`).
> If `${CLAUDE_PLUGIN_ROOT}` is not filled in, it is the folder two levels above this skill's folder; give it to
> every agent you dispatch as `pluginRoot:` in the brief.
> Tool names are Claude Code's; in another assistant use its equivalent
> (`${CLAUDE_PLUGIN_ROOT}/reference/clients.md`).

Records a future feature as one file in `<docsRoot>/plans/` (`targets.json` → `docsRoot`, default `docs`): the
unordered backlog of work not yet started. It **captures** a plan; it implements nothing and touches no code or
other doc. The lifecycle is in `.claude/rules/documentation.md` (*Plans, specifications and the backlog*).

If the user wants it built now, use `/stackfoundry:implement-plan` after capturing it, or just build it.

## Procedure

1. **Clarify just enough**: the intent and the rough scope. A backlog plan may be rough; capture detail when the
   user gives it, and don't interrogate.
2. **Slug**: short kebab-case (`order-export`, `bulk-image-upload`) that collides with no file in `plans/` or
   `specifications/`.
3. **Template**: `<docsRoot>/plans/_template.md`. When the repo has none, use the body of
   `${CLAUDE_PLUGIN_ROOT}/reference/trackers/plan.md` (after its template frontmatter) and mention that
   `/stackfoundry:sync` scaffolds the trackers.
4. **Fill it** in `<docsRoot>/plans/<slug>.md`:
   - line 3 `**Category:** <word>` from the vocabulary in `<docsRoot>/plans/README.md`, the area the feature mostly
     lives in. No vocabulary there: ask the user for the word and say the README lacks one.
   - **Context** (why, the outcome), **Scope** (behaviours a test could check), **Design notes** (as detailed as
     known), **Affected areas**, **Verification**, **Out of scope**. A section stays terse or "TBD" only when it is
     genuinely undecided.
   - **Affected areas** names targets from `targets.json`; for files the user named, `stackfoundry change-targets
     --files <paths>` gives them.
   - **Verification** names the behaviours to exercise and which targets' gates must pass, not copies of the gate
     commands, which drift.
   - Name code by path + symbol, never `file:line` or counts (`.claude/rules/documentation.md`).
5. **Check** with `stackfoundry backlog --section plans`: the new plan is listed with its category and no lint
   line names it.
6. **Report** the path and that it is an unscheduled backlog item; `/stackfoundry:backlog` lists the heap,
   `/stackfoundry:implement-plan` builds one.

## Boundaries

Exactly one new file under `<docsRoot>/plans/`. No code, no spec, no `CLAUDE.md` or rulebook edit, no git writes.

## Tooling

- `Read` the template and the plans README; `Write` the plan.
- `Bash`: `stackfoundry change-targets --files …`, `stackfoundry backlog --section plans`.
