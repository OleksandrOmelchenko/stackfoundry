---
templateVersion: 1
output: .claude/rules/dependency-bumps.md
---
---
description: How any version pin is bumped — classify patch/minor/major first, a major waits for the user, route every finding, move lock-step chains together, read the technology's own release sources, one ecosystem per change.
paths:
{{one "  - \"<glob>\"" line per pin file and lock file in ecosystems.json}}
---

# Dependency and version bumps

Where every pin lives, how it is discovered, applied and gated: `.stackfoundry/ecosystems.json`. The
procedure: `/stackfoundry:bump <ecosystem>`, sequenced by `/stackfoundry:bump-all`. `/stackfoundry:check-updates`
reports; `/stackfoundry:act-on-updates` routes the report. This file holds the rules they share.

## Classify before touching

Every candidate is `patch`, `minor` or **`major`** by semver where semver applies. These are **majors** too, semver
or not: a runtime or SDK line, a framework's compatibility-date or opt-in flag move, a CI runner image rolling to a
new OS, a cloud resource API version, a code generator's major, anything whose upgrade tool rewrites source.

## A major is never applied silently

1. Read **its own release notes and migration guide** (the ecosystem's `sources` and the pack's `upgrade`
   section), not memory, which is stale by construction for versions.
2. Write one paragraph: what breaks **here**, with the files it touches.
3. **Stop for the user's decision.** Patches and minors are applied and gated without asking; a major waits.
4. A declined major goes into `{{deferredFile}}` with its unblock condition. Once applied, its row is deleted in
   the same change.
5. One ecosystem per change, one major per change; commits only when the user asks.

## Route every finding

| Route | When | Handled by |
|---|---|---|
| `bump` | a patch or minor, or a major whose breaking note touches only the pin, config, test setup or expected test values | `/stackfoundry:bump-all <ecosystem>` |
| `migrate` | a major or format migration that rewrites product code in more than one place, adopts a new API shape, or needs a design call | `/stackfoundry:plan-feature`, one plan per migration, never applied inside a sweep |
| `defer` | blocked outside the repo (an upstream release, a hosting runtime) | a row in `{{deferredFile}}` with its check |
| `decide` | an owner decision that is not a version move (runner image, opt-in option, a security floor), with its deadline when the source gives one | the user |
| `watch` | a vulnerability with no real fix yet | re-checked by the next report |
| `machine` | a tool on this machine is outdated or missing | the user runs the install command |
| `—` | nothing to move | nobody |

- **An existing plan wins**: an item a plan already covers cites it and is not planned twice.
- **A vulnerable item is routed by its fix**: a non-major fix is a `bump`, a major fix is routed like any major, no
  fix is a `watch`.
- **A report is fresh** while none of the ecosystem's pin files has moved since its date
  (`git log --since=<report date> -- <pin files>`). A stale ecosystem is discovered again before anyone acts.

## Lock-step chains

The `chains` in `ecosystems.json` list pins that must move together (an SDK band, CI pins, project target
frameworks and the hosting runtime; a framework and its companion packages). A bump moves the whole chain or none
of it.

## After any platform bump

Search the old version string across `CLAUDE.md` files, `.claude/` and `{{docsRoot}}/`. A version a rule depends on
is updated with its reason; one stated as background is deleted (`documentation.md`).

## Never

- Run a deployment or a production workflow to test a bump.
- Hand-edit a lock file, or change a manifest without regenerating its lock file in the same change.
- Touch generated code: a bump is not a regeneration (regenerate through its own procedure).
- Edit an applied migration.
- Stop a service another person or session owns to free a locked build output: ask.
