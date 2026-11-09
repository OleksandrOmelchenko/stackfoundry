---
name: ask-me
description: Turn what this session left open — choices made for the user, follow-ups, open questions, assumptions, unverified steps — into AskUserQuestion prompts, then act on the answers. Use for "ask me".
argument-hint: "[decisions|follow-ups|assumptions|all]"
---

# Ask me

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

The user wants the open ends of this session as questions they can click through, not prose they have to dig out
of earlier messages. The source is the conversation itself: no new research and no new work before the answers.

An argument narrows the harvest: `decisions` (choices made for the user), `follow-ups`, `assumptions` (including
unverified steps), or `all` (the default).

## 1. Harvest

Read back through this conversation, newest first, to the start of the current task (the last request that began
unrelated work). Collect every item that waits on the user:

- **Choices made for them**: "your call", "I went with X", "I chose X because", a default picked where two options
  were reasonable.
- **Follow-ups**: "later", "separate change", "out of scope", a backlog idea raised in passing.
- **Open questions**: "not sure whether", a question asked in prose that got no answer, a closing question whose
  answer never came.
- **Assumptions and gaps**: "I assumed", "presumably", "not verified", "skipped", "could not run", a step the
  summary named as not done.
- In plan mode, the plan file's open questions. Outside it, `TODO`/`FIXME` lines this session's diff added
  (`git diff` and `git diff --cached`, read-only).

## 2. Filter

- **Drop what you can settle yourself.** If the code, the repo's rules (`CLAUDE.md` or `AGENTS.md`, `.stackfoundry/rules/`,
  the stackfoundry profile) or a read-only command answers it, check and settle it instead of asking; mention each in
  one line.
- Drop what the user already answered, and cosmetic trivia nobody would choose differently.
- Merge duplicates: items one decision settles become one question.
- **Nothing left**: say so in one line. Never invent questions to fill the tool.

## 3. Ask

- `AskUserQuestion`: up to 4 questions per call, the most consequential first. More than 4: another round after
  acting on the first; stop after three rounds and list the rest in the reply.
- Each question:
  - one decision, worded so it makes sense without scrolling back, naming the file, feature or command;
  - `header` of 12 characters or fewer;
  - 2–4 options, your recommendation first with "(Recommended)" after its label; each `description` states the
    trade-off rather than restating the label;
  - a list of follow-ups is one `multiSelect` question ("Which of these should happen now?");
  - `preview` when the options are code, config or layout to compare side by side.
- Never ask "should I proceed?" or for approval of a plan: in plan mode that is `ExitPlanMode`'s job.

## 4. Act on the answers

- **Decisions**: apply them, then verify the way the original change was verified (the touched targets' gates).
- **A follow-up picked "now"**: if it acts on what this session found, do it here; if it is a task of its own and
  the host offers a way to start a separate session, propose it there with a complete brief; otherwise name it as a
  follow-up in the reply.
- **A follow-up picked "later"**: offer `/stackfoundry:plan-feature` so it lands in the plans backlog.
- **"Other" with free text**: follow it; if it contradicts an earlier choice, undo that choice first.
- **Git writes stay the user's**: an answer is not a request to commit.
- **Finish** with what changed per answer.

## Tooling

- `AskUserQuestion` works in and out of plan mode. When exactly one yes/no is left at the end of a turn and the host
  has an end-of-turn question tool, use that instead of a separate prompt.
- Read-only `Bash` git for the diff harvest. Host-specific session tools may be deferred: load them with
  `ToolSearch` before the first call.
