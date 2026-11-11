---
name: backlog
description: Categorized list of everything pending — backlog plans, spec follow-ups, open bug-report findings and test-design rows, code TODOs. Use for "what's open", "what's left", or /stackfoundry:backlog [plans|bugs|todos] [category]. Read-only.
argument-hint: "[plans|bugs|todos] [category]"
---

# Backlog

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

`stackfoundry backlog` does the mechanical part. Under the docs root (`targets.json` → `docsRoot`, default `docs`)
it reads every plan's and spec's line-3 `**Category:**`, the `## Follow-ups` bullets of each spec, every open
bug-report finding (⬜ OPEN, ⚠️ PARTIAL), every open test-design row, and `TODO`/`FIXME` comments in tracked code.
This skill adds what a parser cannot: the judgment calls, and a faithful presentation.

## Scope

- **No argument**: every section.
- **`plans`**, **`bugs`**, **`todos`**: one section (several may be combined, one run each).
- **A category word** (the vocabulary is in `<docsRoot>/plans/README.md`): only that category's plans and spec
  follow-ups. Findings and test rows carry no Category, so they are shown unfiltered under their own heading, and
  the reply says so.

## Procedure

1. Run `stackfoundry backlog --section <plans|bugs|todos|all> [--category <word>]`. Exit code 1 means a plan or
   spec has no valid `**Category:**` on line 3: list those under **Lint**. Never add a category yourself; that is
   the author's call (`/stackfoundry:plan-feature`, or the spec's owner).
2. **Check what the parser cannot see.** It reads only findings shaped as the tracker format says
   (`${CLAUDE_PLUGIN_ROOT}/reference/trackers/bug-reports-README.md`). For a bug report or test design that looks
   hand-shaped, run `stackfoundry tracker check <file>`; when it fails, read the file and list its open items by
   hand, marked as such.
3. **Add the judgment**, one line each under **Notes**:
   - a plan whose feature already exists in code → "retire via `/stackfoundry:retire-plan`";
   - an index row in a tracker README that contradicts the report's own markers → "index row stale:
     `/stackfoundry:docs-reconciler`";
   - an untracked file in the plans folder (`git status --porcelain <docsRoot>/plans`) → "uncommitted plan";
   - a report with findings but no status markers → listed, done-ness unknown.
4. **Present** in chat as the CLI prints it: grouped, with `file:line` links, **one item per line**. Never join a
   section into a paragraph, never collapse a section to a count, never re-rank or re-label severities: the source
   documents own those. The one allowed compression is a long spec follow-ups section: counts per category plus
   the path of the saved full output, said explicitly.

## Boundaries

- Read-only. Never edits a plan, spec, report, README row or comment, and never marks anything done. Each
  suggested change points at the skill that owns it: `/stackfoundry:retire-plan`,
  `/stackfoundry:docs-reconciler`, `/stackfoundry:fix-verify`, `/stackfoundry:plan-feature`.
- A listed finding is open according to its document, which may lag the code. Say so when asked whether something
  is really still open, and point at `/stackfoundry:docs-reconciler` (trackers area) or
  `/stackfoundry:fix-verify`.

## Tooling

- `Bash`: `stackfoundry backlog …` (add `--json` when the output feeds a further step), `stackfoundry tracker
  check <file>`, `git status --porcelain`.
- `Read` the reports the parser could not shape. When the tool saves a large output to a file, `Read` it back and
  reproduce the plans, findings and TODO sections line for line.
- Present in chat; publish a page only when the user asks for one to share.
