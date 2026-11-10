# stackfoundry: repo profile

<!-- Written by /stackfoundry:init from the interview and the survey. Owned by the team: edit freely.
     Every role agent reads it first, so keep it short and true. -->

## The product

A Claude Code marketplace (`.claude-plugin/marketplace.json`) with one plugin, `plugins/stackfoundry/`. The plugin
studies any repository, researches each technology in it from current official sources, and writes grounded
rulebooks and target profiles that drive generic role agents and orchestrator skills. It ships procedure and
templates only, never technology content (`.claude/CLAUDE.md`, `docs/design.md`).

## Users and channels

- `plugin`: developers who install it from the public GitHub marketplace and run `/stackfoundry:*` skills in their
  own repos. It runs inside their local Claude Code session and reads their repo, which is untrusted input to every
  agent (a prompt-injection surface).
- `cli`: the helper CLI those skills and the PreToolUse guard hook run locally (`plugins/stackfoundry/scripts/stackfoundry.sh`).
  No network; it reads arbitrary repo content and hook JSON on stdin.
- Contributors run the working tree with `claude --plugin-dir plugins/stackfoundry`.

## What is at stake

- **Safety**: the guard hook (`plugins/stackfoundry/scripts/stackfoundry/guard.py`, wired in `plugins/stackfoundry/hooks/hooks.json`) is what denies
  hand-edits of generated files, forbidden commands and unasked git writes in users' repos. It fails open by design
  (`onFailure: continue`; the launcher exits 0 for `guard` when no Python is found), so a guard bug silently removes
  protection.
- **Data integrity**: skills and the CLI write into users' repos (rulebooks, trackers, `manifest.lock.json`, code).
  A wrong write or a read-only subcommand that writes damages someone else's tree.
- No money, personal data or authentication code.

## Constraints that shape the code

- Python helpers: standard library only, no network calls, JSON for data; Python 3.11 floor; every subcommand says
  whether it writes, and read-only ones never do (`.claude/CLAUDE.md`).
- Runs on Windows, macOS and Linux (CI matrix in `.github/workflows/ci.yml`); the launcher is POSIX `sh`.
- No technology content in the plugin and no real project's internals in skills, agents or templates
  (`.claude/CLAUDE.md`, `.claude/rules/authoring.md`).
- `fixtures/` is test and eval data (`fixtures/README.md`): deliberately imperfect sample repos. Never "fix" a
  fixture to look correct, and never show an agent the `fixtures/*/EXPECTED.md` answer keys.

## Who decides

The owner: release tags (`stackfoundry--v<version>`) and pushes (`.claude/CLAUDE.md`, `docs/release.md`).

## Working agreements

- Git: single branch, work on `main`; commits only when the user asks in that turn; tags and pushes are the owner's
  (enforced as `guards.json` `git.writes: ask`, plus a deny on `claude plugin tag` without `--dry-run`).
- Generated code: the other assistants' plugin files (`targets.json` `generated`), written by
  `scripts/build_clients.py` and denied to hand edits by `guards.json`.
- Evals (`claude plugin eval`) spend real tokens: ask before running them (guarded).
- Docs root: `docs`. Report dates use Europe/Madrid.
- Checks before calling a change done: the four commands in `.claude/CLAUDE.md` (they are the targets' gates).

## Targets

`.stackfoundry/targets.json` is the list; each target's facts are in `.stackfoundry/targets/`.
