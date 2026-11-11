# Render target profiles from the profile, not by hand

**Category:** cli

## Context

`.stackfoundry/targets/<target>.md` is the one generated file with no CLI renderer: init and upgrade fill
`plugins/stackfoundry/reference/templates/target.md` by hand. Rulebooks have `pack render` and `render-rulebook`,
the instruction block has `render-block`, and agents have `render-agent`.

When target template version 2 changed the *Gate* section (an unproven/proven/failed status, never a test count; a
framework with no shuffle option), the BookStore upgrade to 0.3.0 had to apply it by hand-editing every profile's
Gate lines. Hand edits drift, and a template change can't be applied the same way twice.

The outcome: the mechanical parts of a target profile are rendered from `targets.json` and the packs, so an upgrade
regenerates them, and the model writes only the prose.

## Scope

- **`stackfoundry render-target <target> [--write | --out | --diff]`** renders the sections that are facts in the
  profile:
  - **Stack:** one row per pack in `targets.json` `packs`, with its layer from `layers.md` and its rulebook link.
  - **Where things are:** the source and test globs from `paths` and `testPaths`, and the generated globs from
    `generated` with their regenerate command.
  - **Gate:** the build, test and lint commands from `gate`, their preconditions, a status per command from a
    recorded proof, and the shuffle, coverage and mutation commands from `tests[]`.
- **Prose sections:** the one-line summary, oracles, security focus and traps are kept as they are in the existing
  file and never generated.
- **`--write`:** replaces only the rendered sections, marked so the prose around them survives, the way
  `render-block` splices between its markers.
- **`--diff`:** previews the change, as `render-block --diff` does.
- **Skills:** `init`, `sync` and `upgrade` call it instead of filling those sections by hand. A template change to a
  rendered section then reaches every profile on the next upgrade.

## Design notes

- **Where the proof lives** is the open question. A per-command status ("proven on <date>") has to be written down
  somewhere `render-target` can read. Options: a `proven` field per gate command in `targets.json`, or a small
  `.stackfoundry/gates.json` that init's step 5 writes. Settle this first.
- **Section markers:** the rendered sections need markers (an HTML comment per section, as `render-block` uses)
  so the prose between them stays the team's. Existing profiles get the markers once, at the upgrade that ships
  this.
- **Reuse:**
  - the manifest's block-only hashing (`manifest.py` `BLOCK`) extends to the target sections;
  - `block.py` `splice` and `preview` handle the splice and the diff;
  - `rulebooks.py` already renders shared rulebooks from `targets.json`.

## Affected areas

- `cli`: a new `plugins/stackfoundry/scripts/stackfoundry/targets_render.py`, wired in `cli.py`; the `manifest.py`
  hashing.
- `plugin`: `reference/templates/target.md` (markers), and `skills/init`, `skills/sync`, `skills/upgrade`.

## Verification

- A profile rendered from a sample `targets.json` has the Stack, Where and Gate sections the template describes.
- `--write` on a profile with team prose around the sections keeps that prose byte for byte.
- A template change to the Gate section reaches an untouched profile through `upgrade`, and an edited one is
  offered as a merge.
- The `cli` and `plugin` gates pass.

## Out of scope

- Generating the prose sections (summary, oracles, security focus, traps). They stay the model's and the team's.
