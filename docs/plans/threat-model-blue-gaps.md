# Close the open 🔵 gaps of the plugin threat model

**Category:** cli

## Context

The plugin threat model (`docs/security/plugin-threat-model.md`) has its 🔴 and 🟡 gaps fixed. Five 🔵 gaps remain
open: T8, T12, T13, T14 and T17. Each is low severity on its own, either because a host prompt stands in front of it
or because it needs an unusual setup. Together they leave two things weak: controls that change behaviour without
saying so, and no measurement of the "content is data" clauses the whole model leans on. This plan closes them in
an order where the mechanical fixes land first. Each gap's own **Fix** in the threat model is the detailed spec;
this plan sequences them and records the decisions still open.

## Scope

In order, cheapest and most mechanical first:

1. **T17, Cursor hooks:**
   - `scripts/build_clients.py` refuses a relative hook command for `stop` and `subagentStop`.
   - `reference/clients.md` replaces the Cursor *confirm* note with the documented behaviour.
2. **T12, privileged agent frontmatter:**
   - `clients.py` `render_agent` drops or refuses `permissionMode`, `hooks` and `mcpServers` in a materialized
     agent unless the plugin's template sets them.
   - `verify-plumbing .` warns about them in repo mode.
3. **T8, silent extensions:**
   - Every skill and agent names the repo extensions it applied in its report.
   - `extensions check` warns when a `mode: replace` file drops the role's data sentence or its *What you must
     not do* section.
   - It also warns when extension text names the guard, hooks, permission modes, `curl`/`wget` or `--no-verify`.
4. **T13, landing PRs:** `github-prs` `merge` reads `.stackfoundry/*` from the default branch, not the PR's. It
   flags PRs that touch `.stackfoundry/**`, `.claude/**` or instruction files, and lists the commands it will run in
   the one confirmation.
5. **T14, injection resistance:**
   - `tests/test_reference.py` asserts that every agent granted WebFetch or Bash keeps its data sentence.
   - A fixture plants an agent-directed comment and a stub fetched page.
   - An eval case asserts the reviewer reports the planted text and runs nothing beyond its brief.

## Design notes

- **T12:** decide between dropping the keys with a note and refusing to render. Refusing is stricter but blocks a
  team that set `hooks:` on purpose. Recommendation: refuse, and name `/stackfoundry:customize` as the place to
  record an intended exception. Skills can carry `hooks:` too (the skills frontmatter reference); the same check
  should cover a materialized skill.
- **T8:** the report line ("extensions applied: …") belongs in the shared preamble (`scripts/stackfoundry/preamble.py`)
  so no skill copies it.
- **T14:** the eval case spends tokens (`claude plugin eval` is guarded `ask`), so it belongs in the eval lane from
  the what's-next report's item 7, not in the per-commit tests. The `test_reference.py` assertion is free and lands
  first.

## Affected areas

- `cli`: `scripts/stackfoundry/clients.py`, `extensions.py`, `plumbing.py`, `preamble.py`.
- `plugin`: `skills/github-prs`, `reference/clients.md`, `reference/extensions.md`, `evals/`,
  `scripts/build_clients.py`, `fixtures/`.

## Verification

- Each fix has a test that fails on the code before it. This is the same proof used for the 🟡 gaps.
- The `cli` and `plugin` gates pass, along with `verify-plumbing`, `build_clients.py --check` and
  `claude plugin validate --strict`.
- The threat model marks each gap ✅ FIXED with its mitigation, and `stackfoundry tracker check` passes.

## Out of scope

- A release; that is decided separately.
- Proving the other assistants' hooks (the host smoke matrix plan).
- New gaps found while doing this: they go to the threat model with new `T` ids.
