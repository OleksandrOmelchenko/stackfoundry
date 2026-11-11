# Target profiles' rendered sections

**Category:** cli

**Status:** built.

## Why

`.stackfoundry/targets/<target>.md` was the one generated file with no CLI renderer: init and upgrade filled
`reference/templates/target.md` by hand. When target template version 2 changed the Gate lines, the BookStore
upgrade to 0.3.0 had to hand-edit every profile, which drifts and cannot be applied the same way twice.

## Behaviour

- **Rendered sections:** a target profile's *Stack* and *Gate* sections are facts of the profile, rendered between
  `<!-- stackfoundry:begin target-stack|target-gate … -->` and `<!-- stackfoundry:end -->` under their headings.
  Everything else is prose by the model and the team, and is never touched: the summary, *Where things are*,
  *Benchmarks*, *Oracle sources*, *Emphasis*, *Traps*, and notes written after a marker block.
  - **Stack:** one row per pack in `targets.json` `packs`, with its layer (from the id prefix) and a link to its
    rulebook, or "not researched yet".
  - **Gate:** the `build`, `test` and `lint` commands; a status per command; the preconditions; one bullet per
    `tests[]` suite with its command, shuffled run, coverage and mutation lane ("none recorded" or "none yet" where
    absent); the local URL.
- **`stackfoundry render-target <target>`:** prints the profile with its sections rendered.
  - `--write` splices them in, keeping the file's line endings.
  - `--diff` shows the change and the size, and writes nothing.
  - A profile without markers is migrated once: the body under `## Stack` and `## Gate`, up to the next `## `
    heading, is replaced by the marked block. A missing heading is an error.
- **Gate proof:** it lives in `.stackfoundry/gates.json`, written only by `stackfoundry gate record <target>
  --command "<cmd>" --status proven|failed|unproven`.
  - Only a gate or suite command of that target in `targets.json` is accepted.
  - A command missing from the file is `unproven`, so an edited command is unproven again by itself.
  - No dates are kept.
  - `stackfoundry gate list [--json]` shows every command's status.
- **Manifest:** it hashes every stackfoundry marker block in a file. A team edit to a profile's prose leaves it
  `untouched`, so `upgrade` re-renders its sections without asking. A file with one block hashes as before.
- **Skills:** init, sync, upgrade, scaffold-test-harness and setup-mutation record results with `gate record` and
  render with `render-target`; they never edit the two sections by hand. upgrade shows an unmarked profile's first
  migration with `--diff` in its one confirmation.

## Design

- `plugins/stackfoundry/scripts/stackfoundry/target_profile.py`:
  - `commands`, `load_gates`, `status`, `record`, `listing` and `main_gate`;
  - `render` (`_stack`, `_gate`), `splice` and `main_render`.
- `plugins/stackfoundry/scripts/stackfoundry/manifest.py` `sha256`, which hashes every marker block.
- `plugins/stackfoundry/reference/templates/target.md`, template version 3, with the two marker pairs.
- `plugins/stackfoundry/reference/schemas/gates.schema.json`.

## Verification

- `tests/test_target_profile.py` covers:
  - recording, listing and removing proof;
  - refusing an unknown target or command;
  - an edited command reading unproven;
  - the rendered Stack and Gate;
  - migrating an unmarked profile with every other section kept;
  - prose surviving a re-render;
  - CRLF kept, and `--diff` writing nothing;
  - the manifest hash of a profile and of a one-block file;
  - the skills' wiring.
- This repo's own `cli` and `plugin` profiles were migrated, with their gate commands run and recorded.
- The `cli` and `plugin` gates were green.

## Follow-ups (not yet implemented)

- None.
