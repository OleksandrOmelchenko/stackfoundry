# Per-task permissions for desktop scheduled tasks

**Category:** plugin

## Context

A Claude desktop scheduled task takes no command-line flags, so `schedule` writes each scheduled skill's allow rules
into `.claude/settings.local.json` (`stackfoundry schedule rules --write`). Every other session in that clone gets
them too. That is the trade-off `reference/unattended.md` and `reference/clients.md` state.

A task is stored as a `SKILL.md` (`~/.claude/scheduled-tasks/<taskId>/SKILL.md`), and skills can carry
`allowed-tools` in their frontmatter. If the desktop runner honours that for a task, every scheduled skill could carry
exactly its own rules, and nothing would go into the shared settings.

The probe that settles this was not run: the session that built `schedule rules` was refused permission to create a
throwaway scheduled task, so a person runs it.

## Scope

- **The probe, run once by hand in the Claude desktop app:**
  1. Create an ad hoc scheduled task (no schedule) whose prompt is: run `echo stackfoundry-probe` with Bash, then say
     whether it ran or was refused.
  2. Add `allowed-tools: Bash(echo stackfoundry-probe *)` to its `SKILL.md` frontmatter.
  3. Make sure no settings file allows that command, then click **Run now**.
  4. Ran without an approval prompt: frontmatter rules work. A prompt, a stall or a denial: they don't.
  5. Delete the task.
- **If they work:**
  - `stackfoundry schedule rules --write --to task <taskId>` writes the skill's rules into that task's frontmatter,
    owned and rewritable like the settings destination;
  - `schedule` makes it the default;
  - `schedule check` reads it;
  - the local settings carry nothing for scheduled runs.
- **If not:** ask for per-task tool permissions in the Claude desktop app (the upstream request), and keep the local
  settings default. `stackfoundry-radar` watches Claude Code releases and would surface support.

## Design notes

- `scripts/stackfoundry/schedule.py` `write` already records ownership per destination; a `task` destination is one
  more key (`task:<taskId>`) with the frontmatter as the file.
- The frontmatter is the task's own file under the user's home, outside the repo, so it is never committed.

## Affected areas

- `cli` (`schedule.py`), `plugin` (`skills/schedule`, `reference/clients.md`, `reference/unattended.md`).

## Verification

- The probe's result recorded in `reference/clients.md`, replacing its *confirm* line.
- If built: a task written with its rules runs from the desktop app with nothing in the local settings, and
  `schedule check` reads the task's list.

## Out of scope

- Other assistants' schedulers.
