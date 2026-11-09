---
name: research-stack
description: Research or refresh one technology pack (a language, app model, capability or tool) from current official sources, ground it in this repo and regenerate its rulebook. Use when a pack is stale, missing or wrong.
argument-hint: "<pack-id | technology> [--refresh]"
---

# Research stack

Writes or refreshes **one** pack under `.claude/stackfoundry/packs/<pack-id>/` and the rulebook generated from it,
`.claude/rules/<pack-id>.md`. The procedure and the rules for content are
`${CLAUDE_PLUGIN_ROOT}/reference/pack-research.md`; the shape is `${CLAUDE_PLUGIN_ROOT}/reference/schemas/pack.schema.json`.

## 1. Resolve the pack

- A pack id (`app-model-wpf`) or a technology name ("WPF", "Vitest"): match it against the `packs` lists in
  `.claude/stackfoundry/targets.json`. Not in any target → ask which targets use it and which layer it belongs to
  (`${CLAUDE_PLUGIN_ROOT}/reference/layers.md`); it is added to those targets' `packs` in step 4.
- Collect the inputs: versions and where they are pinned (the manifests, `ecosystems.json`), the files that use it
  (`Grep`), the existing conventions (formatter and analyzer config, base classes, the current rulebook), and the
  exposure and stakes of the targets that use it.

## 2. Research

Dispatch `stackfoundry:stack-researcher` with those inputs, `exposure:`/`stakes:` of the targets, and
`output: .stackfoundry-staging/packs/<pack-id>/pack.json` (outside the protected `.claude/`, so the research
survives a refused write). With
`--refresh`, also hand it the current pack, so it reports what changed since `researchedAt` (new releases,
deprecations now in use, changed guidance) and keeps every `repoConvention` the team recorded. Then
`stackfoundry pack check <output>`; errors go back to the researcher, never patched by hand.

## 3. Review the result

- Reject any rule without a source or without grounding; say which.
- **Refresh**: show the diff of rules, categories and upgrade notes against the current pack. A rule the team had
  overridden (a `repoConvention`) keeps its override unless the user drops it.
- Conflicts and questions go to the user in one `AskUserQuestion` round.

## 4. Write

- `.claude/stackfoundry/packs/<pack-id>/pack.json`: move the checked pack in from `.stackfoundry-staging/`, then
  delete the staging folder.
- The rulebook: `stackfoundry pack render <pack.json> --out .claude/rules/<pack-id>.md`. Check its state first with
  `stackfoundry manifest diff --json`: **edited** by the team → show the regenerated text beside the current one and
  ask (take new · keep mine · merge by hand); untouched or new → write it.
- New pack: add it to the targets' `packs`, add its row to the `CLAUDE.md` stackfoundry block, and regenerate the
  code-writer skill of each app model it changes (same edited-file rule).
- `stackfoundry manifest record <pack.json> <rulebook> --template research`.

## 5. Report

What changed (rules added, changed, dropped; new bug categories; upgrade notes), what was not reached, questions left.
Suggest `/stackfoundry:bug-hunt <target>` when new bug categories appeared. Do not commit.

## Boundaries

Writes only the pack, its rulebook, the targets' `packs` lists, the `CLAUDE.md` block row and the code-writer skills it
affects. Never edits product code.

## Tooling
- `Agent` with `subagent_type: "stackfoundry:stack-researcher"`.
- `Grep`/`Read` for the evidence, `Bash` for `stackfoundry manifest diff|record`, `Write`/`Edit` for the files.
- `AskUserQuestion` for conflicts and edited-file choices.
