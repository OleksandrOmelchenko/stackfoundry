# Instruction conflict check

**Category:** plugin

## Context

When two instructions disagree, an agent picks one arbitrarily, and an instruction that names a file, command or
version that no longer holds misleads it. The domain brief rates this capability (`instruction-audit`) as
**expected**; it is **partial** here [cc-memory: https://code.claude.com/docs/en/memory; copilot-instructions:
https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions].

Today's checks are structural:
- the docs-reconciler "instructions" area (`agents/docs-reconciler.md`) checks that paths, globs and symbols exist;
- `render-block --diff` and `size-check` cover the block and sizes;
- `change-targets` reports shadowed globs.

`init` handles only a name collision: it writes `stackfoundry-<name>` beside an existing file. `stack-researcher`
step 7 "Conflicts" weighs official docs against the repo's code conventions, not against the repo's own
instruction files. Nothing compares what a rule *says*.

Two contradictions in this repo went uncaught (source: `docs/reports/2026-11-13-whats-next.md`, items 1, 3, 4):
- pack rulebooks named plugin and CLI versions two releases after the pins had moved;
- channel lists disagreed across `README.md`, `.stackfoundry/product.json` and `.stackfoundry/profile.md`.

The outcome: `init`, `sync` and `docs-reconciler` report every conflict between a stackfoundry file and the repo's
own instructions, or between two stackfoundry files. Each conflict comes with both sides quoted and the question
of which one wins. A conflict is never resolved silently.

## Scope

- **Pin drift (deterministic).** For each pack, a version in `versions[]` whose `pinnedIn` file no longer contains
  that version string is reported as stale, with the file and the version found there when one can be extracted.
  The same check covers the pack's `upgrade.pins`.
- **Rule against team instruction (judgment).** A generated rulebook rule that contradicts a directive in the repo's
  own `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md` or a team rule file is reported, when
  both apply to overlapping paths. Example: the rulebook says to use one test runner, and `CLAUDE.md` names another.
  The text inside the stackfoundry block is excluded, since it is ours.
- **Fact against fact across stackfoundry files.** A product or target fact stated in two stackfoundry files is
  reported when the two disagree: `product.json` against `profile.md`, a target profile against `targets.json`
  outside the rendered sections.
- **Where it runs:**
  - `init`, after the rulebooks are written: any conflicts are listed in the init report, as questions;
  - `sync`, on every run;
  - `docs-reconciler`, in the `instructions` area: conflicts are always flagged, never auto-fixed.
- **Output per conflict:** both files, path + section or rule id, both statements quoted, the overlapping paths, and
  a question: keep the team's (record it as a pack `conflicts` entry so research stops re-proposing the rule), take
  the rule (edit the team file by hand), or scope one of them narrower.

## Design notes

- **Pin drift is a CLI check**, standard library only and read-only: a new `stackfoundry pack check --pins`, or a
  `pins` pass in `volatile-facts`. `pinnedIn` is free text that starts with a repo path. The check must parse the
  path prefix, skip entries whose file is absent, and say "unparseable" rather than guess. It is listed in the
  subcommand help as read-only. `tech-radar`'s stale-pack signal could reuse it.
- **Semantic conflicts need an agent.** Extend the docs-reconciler agent's `instructions` area with a conflicts
  pass:
  - extract imperative statements from the team's instruction files (outside the stackfoundry markers);
  - match them to rulebook rules whose `paths:` overlap the file's scope;
  - judge contradiction, not mere difference.
  It is read-only for this pass, and every hit is a flag.
- **At init**, give `stack-researcher` the repo's instruction files as an input beside "existing rulebooks"
  (`reference/pack-research.md` Inputs), so a conflict is caught while the rule is being written. Its step 7
  records the team's choice the same way it records a convention.
- Keep the always-loaded cost unchanged: no new skill; this goes into existing skills and agents.
- Content in instruction files is data: a directive found there is compared, never followed.

## Affected areas

- `plugin`: `agents/docs-reconciler.md` (conflicts pass), `agents/stack-researcher.md` step 7,
  `reference/pack-research.md` Inputs, `skills/init/SKILL.md` and `skills/sync/SKILL.md` (run and report),
  `skills/docs-reconciler/SKILL.md` (area description), and an eval case.
- `cli`: `plugins/stackfoundry/scripts/stackfoundry/pack.py` (pin drift) and `cli.py` registration, with tests.
- Fixtures: a fixture repo whose `CLAUDE.md` contradicts one rule of its pack, and a pack whose `pinnedIn` version
  is stale.

## Verification

- Unit tests for pin drift:
  - a stale version is reported;
  - a current version is not;
  - a missing file is skipped;
  - an unparseable `pinnedIn` is reported as such.
- An eval case on the contradicting fixture. `docs-reconciler instructions` must flag the conflict with both quotes,
  and must leave both files unchanged.
- `init` on the fixture lists the conflict as a question in its report.
- The `cli` and `plugin` gates pass; `verify-plumbing` and `build_clients.py --check` stay green.

## Out of scope

- Resolving a conflict automatically, in either direction.
- Judging the quality of the team's own instructions, or conflicts between two team files that stackfoundry did
  not write.
- Natural-language conflicts inside a single rulebook (the researcher's job when it writes the pack).
