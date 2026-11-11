---
name: schedule
description: Register the unattended report-only skills (tech-radar, check-updates, whats-next, flaky-watch and more) as scheduled tasks; shows headless and CI alternatives. Asks first. Use for "schedule background checks", "run the radar weekly".
argument-hint: "[skill ...]"
---

# Schedule the unattended skills

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

The unattended skills follow one contract (no questions, no installs, no git writes, one report, a side-effect
check), so they can run on a timer. This skill proposes a cadence, asks once, and registers them as Claude desktop
scheduled tasks, which run on this machine with its toolchain (the discover commands need the real package managers)
and catch up a missed run on the next launch. It creates nothing before the user says yes.

## Proposed cadence

| Skill | Cadence | Cron (local time) | Applies when | Report folder | Also allow |
|---|---|---|---|---|---|
| `check-updates` | weekly | `0 7 * * 1` | `.stackfoundry/ecosystems.json` exists | `dependency-reports` | each ecosystem's `discover` commands; the packs' release-note and migration-guide hosts |
| `tech-radar` | every two weeks | `0 7 1,15 * *` | packs exist under `.stackfoundry/packs/` | `radar` | `WebSearch`; the packs' release-note and migration-guide hosts |
| `stackfoundry-radar` | monthly | `0 7 2 * *` | always | `radar` | `WebFetch(domain:raw.githubusercontent.com)`, `WebFetch(domain:github.com)` |
| `flaky-watch` | nightly or weekly | `0 2 * * *` or `0 2 * * 6` | some target has a `tests[].shuffle` command | `reports` | the suites' `command` and `shuffle` |
| `docs-reconciler` (report-only) | weekly | `0 7 * * 5` | `<docsRoot>` exists | `reports` | none |
| `whats-next` (report-only) | quarterly | `0 7 1 1,4,7,10 *` | `.stackfoundry/product.json` exists | `reports` | none |

Arguments pick a subset. Skip a row whose condition fails and say why. Nightly flaky-watch suits a machine that is on
overnight with the gate preconditions met; otherwise weekly.

## The permission line

Every run follows the unattended contract (`${CLAUDE_PLUGIN_ROOT}/reference/unattended.md`). In Claude Code it runs
with `--permission-mode dontAsk` and an explicit allow list. Whatever the run was not given is denied, never asked,
so a run steered by a page or a test output can still only write its report.

`stackfoundry schedule rules <skill>` prints the list for each skill, one rule per line with its reason. It is built
from the profile, never by hand, and is what the steps below show and write. It holds:

- `"Edit(<docsRoot>/<report folder>/**)"`: on the command line an `Edit` rule covers Write too, and a `Write(…)`
  rule allows nothing.
- `"Bash(sh \"<plugin root>/scripts/stackfoundry.sh\" *)"`: the launcher exactly as the skills call it, with the
  absolute path quoted. A `*` inside the path does not match. The installed plugin's folder changes with each
  version: `upgrade` and `sync` run `stackfoundry schedule rules --rewrite`, which replaces the old path.
- `"Bash(git status *)"`, `"Bash(git log *)"`.
- The row's **Also allow**:
  - a command as `"Bash(<command> *)"`;
  - web access per host as `"WebFetch(domain:<host>)"`, only for the hosts the packs name as release notes or
    migration guides (`upgrade.releaseNotes`, `upgrade.migrationGuides`), plus GitHub for the plugin's own changelog.
    Every host a pack cites would be far wider. Never a bare `WebFetch`, which drops the per-host prompt for every
    other run.

Never `acceptEdits`, which approves any edit or file command in the working directory, and never a flag that
approves every tool.

## Procedure

1. **Read the profile**: `stackfoundry config` (`docsRoot`, `clients`), `.stackfoundry/targets.json` (targets with
   `tests[].shuffle`), the
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

   `<args>` is empty except for docs-reconciler and whats-next, which get `--report` (their report-only mode). Tell
   the user:
   - tasks run while the desktop app is open, and a missed run happens on the next launch;
   - a desktop task takes no command-line flags, so the run gets the rules of *The permission line* from the
     settings: `stackfoundry schedule rules <every approved skill> --write` merges them into
     `.claude/settings.local.json` (this clone, this machine, not committed). It records which rules it owns, so a
     later rewrite replaces only those. `--to project` (the committed `.claude/settings.json`, which every teammate
     and session inherits) only when the user asks for it;
   - the trade-off: those local rules also apply to every other session in this clone. The per-task alternative:
     start each task once from the app (**Run now**) and approve its tools there; the app stores those approvals on
     the task and reuses them on later runs. Offer it when the user would rather not widen the local settings.
     `allowed-tools` in the task's own file does not work (`reference/clients.md`, *Claude desktop scheduled
     tasks*);
   - a task created from an Auto session is saved in Auto mode, where a classifier decides each call: say so, and
     that the user can change the task's mode in the app;
   - `stackfoundry schedule check` afterwards: every approved skill must come back ok, and what is still missing is
     shown, never left for the first run to discover;
   - a command those rules don't allow stalls or is denied.
5. **No scheduling tools in this session**: print, per approved task, the exact title, schedule and prompt to enter
   in the desktop app's scheduled-tasks screen, and show the alternatives below.

## Alternatives (documented, not created unless asked)

**OS scheduler with `claude -p`.** Runs headless from the repo folder with *The permission line*. Shown for
check-updates on an npm repo; fill in the plugin root, the docs root and the row's extras:

```text
# cron (Linux, macOS)
0 7 * * 1 cd /path/to/repo && claude -p "/stackfoundry:check-updates" --permission-mode dontAsk --allowedTools "Edit(docs/dependency-reports/**)" "Bash(sh \"/path/to/plugin/scripts/stackfoundry.sh\" *)" "Bash(git status *)" "Bash(npm outdated *)" >> "$HOME/.cache/stackfoundry-check-updates.log" 2>&1

# Windows Task Scheduler: `stackfoundry schedule rules check-updates --format cmd > stackfoundry-check-updates.cmd`
# writes the .cmd file (UTF-8 with `chcp 65001`, the rules quoted for a Windows command line), then:
schtasks /Create /TN "stackfoundry check-updates" /SC WEEKLY /D MON /ST 07:00 /TR "C:\path\to\stackfoundry-check-updates.cmd"
```

**Another assistant on the OS scheduler.** The same cron or Task Scheduler line with that assistant's headless
command in place of `claude -p` (`${CLAUDE_PLUGIN_ROOT}/reference/clients.md`, *Headless run*), and a prompt that names
the skill in words, since slash forms differ: `codex exec "Run the stackfoundry check-updates skill. This is an
unattended run: ask nothing."`, likewise `copilot -p`, `gemini -p` or `cursor-agent -p`. Each has its own way to
allow the commands a run needs without prompting; say which setting it is from that assistant's docs, and never
suggest a flag that approves every tool.

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
          # <plugin root>: where the action installs plugins on the runner (see its docs)
          claude_args: >-
            --permission-mode dontAsk --allowedTools "Edit(docs/dependency-reports/**)"
            "Bash(sh \"<plugin root>/scripts/stackfoundry.sh\" *)" "Bash(git status *)" "Bash(npm outdated *)"
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

- `Read` / `Bash` for the profile, the repo path and `stackfoundry schedule rules`.
- `ToolSearch` (`scheduled task`) to load the scheduled-tasks tools, then their list and create (or update) calls.
- `AskUserQuestion` once, at step 3.
