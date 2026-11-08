---
name: plan-execute
description: Plan first, then execute immediately without plan mode or approval; still asks about genuine open decisions. Use for "plan execute", "plan and execute", "inline plan", "plan it out then just do it".
---

# Plan and execute

Think the implementation through before editing any code, with the same discipline as
`/stackfoundry:with-plan`, but skip the approval pause: state the plan briefly, then start building in the same
turn.

## In practice

1. **Explore first**: the relevant code, the patterns and utilities to reuse, every file the change will touch.
   With a repo profile, `stackfoundry change-targets --files <planned paths>` names the targets and specialists.
2. **State the plan** as ordinary text, not a plan-mode step: the approach, the files, what it reuses, and how it
   will be verified (the touched targets' gates from `targets.json`). A heads-up, not a document to review.
3. **Ask only what is genuinely the user's call**: a decision the code and the repo's conventions cannot settle and
   no reasonable default covers. That is the one thing allowed to pause execution, and only for that part.
4. **Implement immediately** once the plan is stated and any such question answered, through
   `/stackfoundry:write-code` for the conventions.
5. **Verify normally.** This skill changes only whether the plan is approved before building.

## Don't skip the planning step

Not because the change turns out small: the value is thinking through the approach and the file list before
touching code, especially when the fix looks obvious. When the user already named every file and the exact change,
the stated plan can be a sentence or two, but state it before editing.

## Committing

The task ends at **verification, not a commit**. Git writes are the user's (the profile's working agreements,
enforced by `guards.json` → `git`); stating a plan and carrying it out is not permission to commit. Leave the work
in the tree and say what is ready to commit.

## Scope

Per task. A later, unrelated request is judged on its own unless the user asks for this again.

## Related

`/stackfoundry:with-plan` stops for approval; `/stackfoundry:elaborate-plan` adds a test design and a quality
sweep; `/stackfoundry:implement-only` suppresses verification, a separate choice the user makes explicitly.

## Tooling

- **Never call `EnterPlanMode`/`ExitPlanMode` here**: that pause belongs to `with-plan`.
- Explore read-only first (`Explore` agents for broad discovery, `Read`/`Grep`/`Glob` for a known area).
- `AskUserQuestion` only for a decision the plan cannot proceed without, never as a substitute approval gate.
- Read-only git is fine for the report; staging and committing are not, unless asked in this turn.
