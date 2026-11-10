# Prove every advertised assistant

**Category:** repo

## Context

0.2.0 ships manifests, marketplaces and guard hooks for Codex, GitHub Copilot, Cursor and Gemini CLI, generated from
the Claude Code source by `scripts/build_clients.py`. Only Claude Code is proven end to end; Copilot CLI is proven
for install and skills only. The smoke table in `docs/release.md` says "not run yet" for Codex, Cursor and Gemini
CLI. `reference/clients.md` still marks several facts *confirm*:
- the variable that carries Copilot's plugin root;
- whether Cursor's `allow` keeps its own prompts;
- whether Codex runs hooks from a marketplace install.

The domain brief rates two capabilities as **table stakes** that are only **partial** here:
- `valid-manifest-per-client`: a host skips a plugin whose manifest it cannot load [cc-plugins-ref:
  https://code.claude.com/docs/en/plugins-reference; copilot-cli-plugins:
  https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-cli-plugins; codex-plugins:
  https://learn.chatgpt.com/docs/plugins];
- `marketplace-install` [cc-plugin-install: https://code.claude.com/docs/en/plugins/install].

Source: `docs/reports/2026-11-10-whats-next.md`, item 2.

The outcome is that every assistant the README lists has been installed and exercised, or is marked experimental
until it has.

## Scope

- **Per assistant** (Codex, Cursor, Gemini or its successor, and the rest of Copilot), the four smoke steps of
  `docs/release.md` are run and their results recorded in its table:
  1. marketplace add and install from a clone;
  2. skills and agents listed;
  3. the guard refuses a generated-file edit in a profiled scratch repo;
  4. a plain request starts a skill;
  5. a repo extension is applied.
- **Every *confirm* in `reference/clients.md`** is settled with the evidence, or stays *confirm* with what blocked
  it.
- **Defects** in the generated files or the guard adapters are fixed in their source (`build_clients.py`,
  `guard.py`), with a test per defect.
- **The README** marks any assistant whose run fails, or could not be done, as experimental, with a link to the
  table.

## Design notes

- Use an isolated home per assistant (as with `COPILOT_HOME` for Copilot) so the machine's own setup is untouched.
- Headless prompts name the skill in words (`reference/clients.md`, Headless run). Never pass a flag that approves
  every tool. A permission classifier that refuses a run is recorded, not worked around.
- A scratch repo scaffolded from `fixtures/python-fastapi` with its profile gives a guarded generated folder
  (`app/generated/**`) and a domain brief, so one scaffold covers the guard, a plain request and `whats-next`.
- Record versions (the assistant CLI's version) in the table, since behaviour moves between releases.

## Affected areas

- `repo`: `docs/release.md`, `README.md`.
- `plugin`: `plugins/stackfoundry/reference/clients.md`, `scripts/build_clients.py` when a generated file is wrong.
- `cli`: `plugins/stackfoundry/scripts/stackfoundry/guard.py` when an adapter is wrong.

## Verification

- Every row of the smoke table has a dated result or a stated blocker.
- Every fix lands with a regression test (`tests/test_build_clients.py`, `tests/test_guard_clients.py`).
- The `cli` and `plugin` gates pass.

## Out of scope

- Adding new assistants (`docs/plans/antigravity-channel.md` covers the Gemini successor).
- CI automation of these runs: each needs a signed-in assistant.
