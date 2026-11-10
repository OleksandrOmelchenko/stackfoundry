# Context budgets per assistant

**Category:** cli

## Context

Everything stackfoundry generates into a repo is read by an assistant, and every always-loaded line costs every
turn. The domain brief rates `instruction-size-budgets` as **table stakes**:
- Claude Code advises under 200 lines per CLAUDE.md;
- Cursor advises rules under 500 lines;
- skills are advised under 500 lines and about 5000 tokens;
- Codex stops adding AGENTS.md files at 32 KiB by default.

Sources for these limits: [cc-memory: https://code.claude.com/docs/en/memory; cursor-rules:
https://cursor.com/docs/context/rules; skills-spec: https://agentskills.io/specification; codex-agents-md:
https://learn.chatgpt.com/docs/agent-configuration/agents-md]. It rates `low-context-cost` as **expected**: hosts
show a plugin's every-turn token cost before install [cc-plugin-install:
https://code.claude.com/docs/en/plugins/install].

Its weaknesses "Silent truncation past a host's size limit" and "Context bloat from generic overviews" both apply,
and a 2026 evaluation found repository context files raised inference cost by more than 20% without generally
raising task success [agents-md-eval: https://arxiv.org/abs/2602.11988].

Today stackfoundry caps only skill and agent descriptions (`plugins/stackfoundry/scripts/stackfoundry/plumbing.py`
`SKILL_CAP`, `AGENT_CAP`). `reference/pack-research.md` "Output size" is advice. The plugin's own listing (every
description, loaded each session) has no total budget.

Source: `docs/reports/2026-11-10-whats-next.md`, item 3.

The outcome is that no generated file exceeds what its assistant reads, and the always-on cost of the plugin and of
a repo's generated files is known and bounded.

## Scope

- **Limits:** a per-assistant table of size limits in `reference/clients.md`, each cited. Covers lines and bytes for
  instruction files, path-scoped rules, skills and agents, and Codex's combined AGENTS.md limit.
- **Repo check:** `stackfoundry` checks every generated file in a repo against the limits of the assistants in
  `config.json` `clients`: rulebooks and their copies, instruction blocks, code-writer skills and materialized
  agents. A file over a hard limit is an error, and one near a soft advice is a warning.
- **Plugin check:** the plugin's always-on listing (all skill and agent descriptions) has a total budget enforced
  by `verify-plumbing` in plugin mode, so the next new skill shows its cost.
- **Wiring:** `init`, `sync`, `upgrade` and `research-stack` run the check after writing, and `pack check` warns when
  a pack would render past the rule limit.
- **Visibility:** the check reports the sizes it measured, so the cost is visible, not only the breaches.

## Design notes

- The natural home is `globs-check`'s sibling in `scripts/stackfoundry/checks.py`, or a new `stackfoundry size-check`.
  The limits table must come from one place: `clients.py` next to `RULE_FORMATS` and `AGENT_FORMATS`, with
  `reference/clients.md` citing the sources.
- **Measure what the host loads:** the rendered copy (`render-rule` output) for each client, and for an instruction
  file only the stackfoundry block, since the team owns the rest. Token estimates are approximate; bytes and lines
  are exact, so budget on those and report tokens as an estimate.
- **Pack rulebooks:** a size breach is fixed by research-stack tightening the pack, never by truncating the render.

## Affected areas

- `cli`: `plugins/stackfoundry/scripts/stackfoundry/clients.py`, `checks.py` or a new module, `plumbing.py`,
  `pack.py`, `cli.py`.
- `plugin`: `plugins/stackfoundry/reference/clients.md`, `reference/pack-research.md`, skills `init`, `sync`,
  `upgrade`, `research-stack`.

## Verification

- Unit tests:
  - a rulebook over a client's limit fails, one under it passes;
  - the stackfoundry block alone is measured;
  - the plugin's listing budget fails when a description is added past it.
- The check passes on this repo's own profile and on the fixtures' profiles.
- The `cli` and `plugin` gates pass.

## Out of scope

- Shortening existing pack rulebooks (a research-stack refresh does that when the check flags one).
- Measuring task success (`behavioral-evals` and `measured-uplift`, item 7 of the report).
