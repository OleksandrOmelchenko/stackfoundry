---
name: schedule
description: Register stackfoundry's unattended skills (check-updates, tech-radar, stackfoundry-radar, flaky-watch, report-only docs-reconciler) as scheduled tasks with a proposed cadence; shows claude -p and GitHub Actions alternatives. Asks first.
argument-hint: "[skill ...]"
disable-model-invocation: true
---

# Schedule the unattended skills

> **Portable form.** `stackfoundry <subcommand>` here means
> `sh "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.sh" <subcommand>` (Windows without `sh`:
> `pwsh -NoProfile -File "${CLAUDE_PLUGIN_ROOT}/scripts/stackfoundry.ps1" <subcommand>`).
> If `${CLAUDE_PLUGIN_ROOT}` is not filled in, it is the folder two levels above this skill's folder; give it to
> every agent you dispatch as `pluginRoot:` in the brief.
> Tool names are Claude Code's; in another assistant use its equivalent
> (`${CLAUDE_PLUGIN_ROOT}/reference/clients.md`).

The unattended skills follow one contract (no questions, no installs, no git writes, one report, a side-effect
check), so they can run on a timer. This skill proposes a cadence, asks once, and registers them as Claude desktop
scheduled tasks, which run on this machine with its toolchain (the discover commands need the real package managers)
and catch up a missed run on the next launch. It creates nothing before the user says yes.

## Proposed cadence

| Skill | Cadence | Cron (local time) | Applies when |
|---|---|---|---|
| `check-updates` | weekly | `0 7 * * 1` | `.stackfoundry/ecosystems.json` exists |
| `tech-radar` | every two weeks | `0 7 1,15 * *` | packs exist under `.stackfoundry/packs/` |
| `stackfoundry-radar` | monthly | `0 7 2 * *` | always |
| `flaky-watch` | nightly or weekly | `0 2 * * *` or `0 2 * * 6` | some target has a `tests[].shuffle` command |
| `docs-reconciler` (report-only) | weekly | `0 7 * * 5` | `<docsRoot>` exists |

Arguments pick a subset. Skip a row whose condition fails and say why. Nightly flaky-watch suits a machine that is on
overnight with the gate preconditions met; otherwise weekly.

## Procedure

1. **Read the profile**: `.stackfoundry/targets.json` (`docsRoot`, targets with `tests[].shuffle`), the
   presence of `ecosystems.json` and packs, and the repo's absolute path (`git rev-parse --show-toplevel`). No
   profile: say "run `/stackfoundry:init` first" and stop.
2. **Load the scheduling tools**: `ToolSearch` with the query `scheduled task`. When they load, list the existing
   tasks and match on the task ids below, so nothing is registered twice (an existing one is offered for update).
3. **Ask once** (`AskUserQuestion`): a multi-select over the applicable rows, and for flaky-watch nightly vs weekly.
   Show each task's id, cadence and prompt before asking.
4. **Create** each approved task with the create tool: `taskId` `stackfoundry-<skill>-<repo folder name>`, a title,
   a one-line description, the cron expression, and a self-contained prompt (each run starts with no memory):

   ```text
   Work in the repository at <absolute repo path>. Run /stackfoundry:<skill> <args>.
   This is an unattended run: ask nothing; anything that needs a decision goes into the report.
   ```

   `<args>` is empty except for docs-reconciler, which gets `--report` (its report-only mode). Tell the user that tasks run
   while the desktop app is open and a missed run happens on the next launch, and that a command the session's
   permissions do not allow stalls or is denied: allow the ecosystems' `discover` commands and the suites' test
   commands in `.claude/settings.json` → `permissions.allow` (the user edits it) before relying on the schedule.
5. **No scheduling tools in this session**: print, per approved task, the exact title, schedule and prompt to enter
   in the desktop app's scheduled-tasks screen, and show the alternatives below.

## Alternatives (documented, not created unless asked)

**OS scheduler with `claude -p`.** Runs headless from the repo folder; `acceptEdits` lets it write the report, and any
command it needs must be allowed in settings or with `--allowedTools`:

```text
# cron (Linux, macOS)
0 7 * * 1 cd /path/to/repo && claude -p "/stackfoundry:check-updates" --permission-mode acceptEdits >> "$HOME/.cache/stackfoundry-check-updates.log" 2>&1

# Windows Task Scheduler
schtasks /Create /TN "stackfoundry check-updates" /SC WEEKLY /D MON /ST 07:00 /TR "cmd /c cd /d C:\path\to\repo && claude -p \"/stackfoundry:check-updates\" --permission-mode acceptEdits"
```

**GitHub Actions** with `anthropics/claude-code-action`, which installs the plugin from its marketplace. The runner
needs the same toolchain the discover commands use (add the setup steps), and the report stays on the runner unless
the job uploads it or opens a pull request (that write is the user's choice). Pin each action per the repo's policy:

```yaml
name: stackfoundry check-updates
on:
  schedule:
    - cron: "0 7 * * 1"
  workflow_dispatch:
permissions:
  contents: read
jobs:
  check-updates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<pinned version>
      # toolchain setup steps for each ecosystem's discover commands go here
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          plugin_marketplaces: https://github.com/OleksandrOmelchenko/stackfoundry.git
          plugins: stackfoundry@stackfoundry
          prompt: /stackfoundry:check-updates
          claude_args: --permission-mode acceptEdits
      - uses: actions/upload-artifact@<pinned version>
        with:
          name: dependency-report
          path: docs/dependency-reports/
```

Write this workflow only when the user asks, at the path they choose. Cloud routines suit only the web-research
skills (tech-radar, stackfoundry-radar): they clone fresh and may not load repo-enabled plugins or have the
toolchain.

## Boundaries

Nothing is created, updated or deleted before the user's yes; existing tasks are never removed. No workflow file,
settings change or git write unless the user asks for that exact action.

## Tooling

- `Read` / `Bash` for the profile and the repo path.
- `ToolSearch` (`scheduled task`) to load the scheduled-tasks tools, then their list and create (or update) calls.
- `AskUserQuestion` once, at step 3.
