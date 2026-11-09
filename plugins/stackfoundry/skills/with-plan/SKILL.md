---
name: with-plan
description: Force plan mode and user approval before any implementation, even for a trivial-looking task. Use when the user says "plan first", "with plan", "plan before executing", or "don't just start coding".
---

# With plan (plan, approve, then build)

> **Portable form.** `stackfoundry <subcommand>` here means
> `sh "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.sh" <subcommand>` (Windows without `sh`:
> `pwsh -NoProfile -File "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.ps1" <subcommand>`).
> If `${CLAUDE_PLUGIN_ROOT}` is not filled in, it is the folder two levels above this skill's folder; give it to
> every agent you dispatch as `pluginRoot:` in the brief.
> Tool names are Claude Code's; in another assistant use its equivalent
> (`${CLAUDE_PLUGIN_ROOT}/reference/clients.md`).

Plan this task before editing any code, **even if it looks small enough to skip planning**. The user asked for a
plan-first workflow before seeing how big the change would be; that overrides the usual judgment about whether a
task deserves a plan.

## In practice

1. Edit nothing but the plan file until a plan is written and approved.
2. **Explore first**, with the same diligence as for a task you judged non-trivial: the relevant code, the
   existing patterns and utilities to reuse, every file the change will touch. `stackfoundry change-targets --files
   <planned paths>` names the targets and the specialists the change will call in, when the repo has a profile.
3. **Write a concise plan**: context (why, what prompted it), approach (what changes, in which files, reusing
   what), and how it will be **verified** (the gates of the targets it touches, from `targets.json`, and any check
   only the user can do).
4. Get approval, then implement and verify normally: through `/stackfoundry:write-code` for the conventions and the
   target gates for verification. This skill front-loads the planning; it changes nothing after approval.

## Don't talk yourself out of it

Not because the diff turns out to be one line, not because the fix is obvious. Deciding mid-task that it is small
enough to skip is the shortcut this skill exists to prevent. When nothing is left to decide (the user named every
file and the exact change, or an approved plan from an earlier turn covers it), the plan can be short, but still
present it for confirmation.

## Committing

The task ends at **verification, not a commit**. Git writes are the user's (the profile's working agreements,
enforced by `guards.json` → `git`): carrying out an approved plan is not permission to commit, and a commit asked
for earlier in the conversation does not carry forward. Leave the work in the tree and say what is ready to commit.

## Scope

Per task. A later, unrelated request is judged on its own unless the user asks for this again.

## Related

`/stackfoundry:plan-execute` states the plan and goes without approval. `/stackfoundry:elaborate-plan` adds a test
design and a quality sweep. `/stackfoundry:implement-only` suppresses verification; it is a separate choice the
user makes, never one to combine on your own.

## Tooling

- Call `EnterPlanMode` regardless of its own "non-trivial tasks only" guidance: the user already decided.
- Explore read-only (`Explore` agents for broad discovery, `Read`/`Grep`/`Glob` for a known area), write the plan
  to the file the system message names, use `AskUserQuestion` only for genuine open decisions, then
  `ExitPlanMode` to request approval.
- After approval, verify as the task and the repo call for. Read-only git (`status`, `diff`, `log`) is fine for the
  report; staging and committing are not, unless asked in this turn.
