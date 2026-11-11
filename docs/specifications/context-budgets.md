# Context budgets per assistant

**Category:** cli

**Status:** built.

## Why

Everything stackfoundry generates into a repo is read by an assistant, and every always-loaded line costs every turn.
Hosts advise or enforce size limits, and a file past a hard one is silently cut. The plugin's own skill and agent
descriptions are loaded into every session's listing. Until this was built, only single descriptions were capped,
so a rulebook, an instruction file or the whole listing could grow without anyone seeing the cost.

## Behaviour

- **Limits** live in one table, `scripts/stackfoundry/clients.py` `LIMITS`, cited in `reference/clients.md` (*Size
  limits*):
  - Claude Code: a `CLAUDE.md` under 200 lines (advice);
  - Cursor: a rule under 500 lines (advice);
  - every assistant: a `SKILL.md` under 500 lines and about 5000 tokens (advice);
  - Codex: the `AGENTS.md` files on a path, combined, up to 32 KiB (where it stops reading).
- **`stackfoundry size-check`** measures, for the assistants in `config.json` `clients`:
  - each instruction file the assistants read, whole, plus the stackfoundry block inside it;
  - every canonical rulebook and each assistant's copy;
  - the repo's skills in each skills folder `stackfoundry outputs` lists;
  - the materialized agents.

  It lists every file's lines, bytes and estimated tokens (bytes/4). A file past a hard limit is an error (exit 1),
  and one past advice is a warning (exit 0). A limit applies only to the host that states it: a rule copy for
  Claude Code has no cited limit, so it is listed without a verdict.
- **Plugin listing budget:** `verify-plumbing` in plugin mode errors when the skill and agent descriptions together
  pass `scripts/stackfoundry/plumbing.py` `LISTING_CAP`. It prints the total and the cap. The cap was set at the size
  of the time plus about 15% headroom, so the next additions show their cost. Raising it is a decision, recorded
  beside the constant.
- **Pack size:** `stackfoundry pack check` warns when a pack would render past the strictest line advice for a
  path-scoped rule (`pack.py` `RULE_LINES`, derived from `LIMITS`). Such a rulebook is tightened by refreshing its pack,
  never by truncating the render.
- **Wiring:** `init`, `sync`, `upgrade` and `research-stack` run `size-check` after writing.

## Design

- `scripts/stackfoundry/sizes.py`: `measure`, `check` and `main`, wired in `cli.py` as `size-check`.
  - It finds instruction files through `block.instruction_files`, the block through `block.BLOCK`, and the copies
    and skills folders through `clients.RULE_FORMATS` and `clients.outputs`.
- `scripts/stackfoundry/plumbing.py`: the listing total, accumulated in `check`, against `LISTING_CAP`.
- `scripts/stackfoundry/pack.py`: `check` renders the pack and compares its lines with `RULE_LINES`.

## Verification

`tests/test_size_check.py` covers:
- the files measured;
- the block measured on its own;
- advice and hard-limit verdicts per host;
- the exit codes;
- the shipped listing within budget, and a lowered cap failing;
- the pack size warning.

The check passes on this repo's own profile, and the `cli` and `plugin` gates were green.

## Follow-ups (not yet implemented)

- Antigravity CLI's limits, once its format is researched (`docs/plans/antigravity-channel.md`).
