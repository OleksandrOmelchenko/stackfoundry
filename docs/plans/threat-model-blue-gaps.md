# Close the open 🔵 gaps of the plugin threat model

**Category:** cli

## Context

The plugin threat model (`docs/security/plugin-threat-model.md`) has its 🔴 and 🟡 gaps fixed. Seven 🔵 gaps remain
open: T8, T10, T12, T13, T14, T17 and T18. Each is low severity on its own, either because a host prompt stands in
front of it or because it needs an unusual setup. Together they leave three things weak: the launcher's trust in
PATH, controls that fail silently, and no measurement of the "content is data" clauses the whole model leans on.
This plan closes them in an order where the mechanical fixes land first. Each gap's own **Fix** in the threat model
is the detailed spec; this plan sequences them and records the decisions still open.

## Scope

In order, cheapest and most mechanical first:

1. **T10, the launcher and PATH:** `scripts/stackfoundry.sh` runs Python only from an absolute path. With `.`, or
   an empty entry, in PATH, a `python3` planted in the repo is never executed.
2. **T18, silent fail-open:**
   - `sync`'s drift table runs `stackfoundry guard --check`.
   - In Claude Code, a `guards.json` that exists but cannot be evaluated produces a `systemMessage` warning. It
     still blocks nothing.
3. **T17, Cursor hooks:**
   - `scripts/build_clients.py` refuses a relative hook command for `stop` and `subagentStop`.
   - `reference/clients.md` replaces the Cursor *confirm* note with the documented behaviour.
4. **T12, privileged agent frontmatter:**
   - `clients.py` `render_agent` drops or refuses `permissionMode`, `hooks` and `mcpServers` in a materialized
     agent unless the plugin's template sets them.
   - `verify-plumbing .` warns about them in repo mode.
5. **T8, silent extensions:**
   - Every skill and agent names the repo extensions it applied in its report.
   - `extensions check` warns when a `mode: replace` file drops the role's data sentence or its *What you must
     not do* section.
   - It also warns when extension text names the guard, hooks, permission modes, `curl`/`wget` or `--no-verify`.
6. **T13, landing PRs:** `github-prs` `merge` reads `.stackfoundry/*` from the default branch, not the PR's. It
   flags PRs that touch `.stackfoundry/**`, `.claude/**` or instruction files, and lists the commands it will run in
   the one confirmation.
7. **T14, injection resistance:**
   - `tests/test_reference.py` asserts that every agent granted WebFetch or Bash keeps its data sentence.
   - A fixture plants an agent-directed comment and a stub fetched page.
   - An eval case asserts the reviewer reports the planted text and runs nothing beyond its brief.

## Design notes

- **T10:** mirror `gitutil.py` `git_exe`, which already refuses a relative git. `stackfoundry.ps1` already requires
  `IsPathRooted`, so only the POSIX launcher changes. Resolve each candidate with `command -v` and require it to
  start with `/` (or a drive letter under Git Bash).
- **T18:** the `systemMessage` field is confirmed for Claude Code only (`reference/clients.md`). Other hosts keep the
  silent no-opinion until their field is confirmed, which the host smoke matrix plan (`host-smoke-matrix.md`) can
  settle.
- **T12:** decide between dropping the keys with a note and refusing to render. Refusing is stricter but blocks a
  team that set `hooks:` on purpose. Recommendation: refuse, and name `/stackfoundry:customize` as the place to
  record an intended exception.
- **T8:** the report line ("extensions applied: …") belongs in the shared preamble (`scripts/stackfoundry/preamble.py`)
  so no skill copies it.
- **T14:** the eval case spends tokens (`claude plugin eval` is guarded `ask`), so it belongs in the eval lane from
  the what's-next report's item 7, not in the per-commit tests. The `test_reference.py` assertion is free and lands
  first.

## Affected areas

- `cli`: `plugins/stackfoundry/scripts/stackfoundry.sh`, `scripts/stackfoundry/guard.py`, `clients.py`,
  `extensions.py`, `plumbing.py`, `preamble.py`.
- `plugin`: `skills/sync`, `skills/github-prs`, `reference/clients.md`, `reference/extensions.md`, `evals/`,
  `scripts/build_clients.py`, `fixtures/`.

## Verification

- Each fix has a test that fails on the code before it. This is the same proof used for the 🟡 gaps.
- T10: a repo with a planted `python3` and `.` first in PATH; the launcher does not run it.
- T18: a broken `guards.json` gives a Claude Code `systemMessage` and `sync` reports it.
- The `cli` and `plugin` gates pass, along with `verify-plumbing`, `build_clients.py --check` and
  `claude plugin validate --strict`.
- The threat model marks each gap ✅ FIXED with its mitigation, and `stackfoundry tracker check` passes.

## Out of scope

- A release; that is decided separately.
- Proving the other assistants' hooks (the host smoke matrix plan).
- New gaps found while doing this: they go to the threat model with new `T` ids.
