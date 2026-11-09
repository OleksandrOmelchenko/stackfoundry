---
name: implement-only
description: Make a code change WITHOUT building, testing, running, regenerating, migrating or starting services, so a parallel session on the same tree is not clobbered. Use for "just implement it", "don't build or test", "code only".
---

# Implement only

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

Write the code change and stop. **Every machine-level action a parallel session could depend on is off-limits**:
builds, test runs, service starts and stops, database changes, code generation, dependency installs. This skill
deliberately overrides any standing "always verify before declaring done" rule for this task. It lowers the bar for
what gets executed, never for the code.

## Why

Two sessions sharing one working tree share its build outputs, its running services and ports, its local database
and its generated folders:

- a build or test run races the other session's build on the same output folders, or fails on files a running
  process holds, and can leave a half-written output behind;
- a restart or a killed process takes down a service the other session is testing against;
- a schema sync, migration, seed or reset mutates the database under the other session; integration suites that
  reset data between tests are the worst case;
- a regeneration (client, scaffold, codegen) rewrites a generated folder from whatever source or service happens to
  be running at that moment;
- an install rewrites lock files and the shared dependency folder;
- `git checkout`, `restore`, `stash`, `reset` or `clean` discards the other session's uncommitted work in this same
  tree.

## What is forbidden here

Derived from the repo, not from a fixed list of tools:

1. **Every gate and test command** in `.stackfoundry/targets.json`: each target's `gate.build`,
   `gate.test`, `gate.lint`, and each `tests[]` entry's `command`, `affectedCommand`, `shuffle`, `coverage` and
   `mutation`. Lint is borderline (process-local, but it can rewrite files the other session is editing): skip it
   unless the user asks.
2. **What the gate preconditions name**: starting, stopping or restarting the services, containers and processes
   in `gate.preconditions`, and any dev server or browser preview that would bind a port.
3. **Every regeneration**: the steps in `guards.json` → `generated[].regenerate` and in the target profiles'
   *Generated* lines. Generated files may be read freely and are never hand-edited.
4. **Everything `guards.json` → `commands` denies or asks about.** Don't reach for those here at all.
5. **The classes the profile may not list**: package installs and updates, schema or migration application,
   database seeds and resets, process or port kills, destructive git.
6. **Delegation** to anything that does the above: `/stackfoundry:run-tests`, `write-tests`, `fix-tests`,
   `review-tests`, `fix-verify`, `debug`, `quality-sweep`, `setup-mutation`, `scaffold-test-harness`,
   `write-benchmarks`, `run-benchmarks`, `bump`, `bump-all`, `sync`, and the `test-runner`, `test-writer`,
   `test-fixer`, `test-reviewer`, `fix-verifier`, `web-fix-verifier`, `code-verifier`, `debugger` and
   `benchmark-writer` agents. Read-only reviewers only when the user asks.

No profile: apply the same classes by judgment, from the repo's own build files and scripts.

## Allowed

Reading, searching and editing files; read-only git (`status`, `diff`, `log`, `show`); the read-only `stackfoundry`
subcommands (`change-targets`, `select-tests`, `backlog`). Correctness comes from reading, not running:

- read the real signature or type you call, including generated code;
- search for every call site of anything you change: a missed one is what the skipped build would have caught;
- follow the conventions through `/stackfoundry:write-code` (its gate step is suppressed here);
- prefer targeted edits to whole-file rewrites, which are likelier to stomp a concurrent edit.

## Contract-level changes

When the change would normally need a regeneration, a migration or a schema sync, **still write the source
change** and record the skipped step as a follow-up. If code you must write depends on an artifact that is not
generated yet (a scaffolded property, a client method), write everything that does not depend on it and say plainly
which part is blocked on which step.

## Report

End with a block the user can act on later:

```text
Changed:   <path + symbol, one line each>
NOT run:   <the classes skipped: build, tests, regeneration, migrations, service restarts>
To verify: <the exact commands, in order: `stackfoundry select-tests --files <changed>` and the touched targets'
            gates, plus each skipped regeneration>
Risk:      <what a build or test would most likely have caught: unverified assumptions, wide blast radius, a change
            to a shared target>
```

Say "unverified" plainly; never claim it builds or passes.

## Scope

Per task. If the user later says to build, test or restart, do it: an explicit instruction wins over this skill.
If the user asks for a commit, stage only the files you touched, never `git add -A` or `git add .`, which would
sweep in the other session's work.

## Tooling

- `Read`/`Grep`/`Glob`/`Edit`/`Write`, read-only git through `Bash`.
- `Bash` for `stackfoundry select-tests --files … --json` and `stackfoundry change-targets`, to compute the
  To-verify list without running it.
- The guard hook still applies; nothing here should come near it.
