---
name: claude-code-plugin-code-writer
description: Write or change stackfoundry skills, agents, reference files and manifests the repo's way — tool grants that cover the body, description caps, full briefs, no technology content. Use when editing the plugin's skills, agents or reference.
---

# Claude Code plugin code writer

Write procedure that looks like the procedure already here. The rules live in the rulebooks below, which are
authoritative; this skill is the decision procedure. Read them before editing.

| Read first | Before touching |
|---|---|
| [`authoring`](../../rules/authoring.md) | anything under `plugins/` (the repo's own authoring rules) |
| [`app-model-claude-code-plugin`](../../rules/app-model-claude-code-plugin.md) | `skills/**`, `agents/**`, `reference/**`, `hooks/**`, `.claude-plugin/**` |
| [`capability-claude-code-marketplace`](../../rules/capability-claude-code-marketplace.md) | `.claude-plugin/marketplace.json`, `docs/release.md` |
| [`tooling-claude-plugin-eval`](../../rules/tooling-claude-plugin-eval.md) | `plugins/stackfoundry/evals/**`, `fixtures/**` |
| [`tooling-unittest`](../../rules/tooling-unittest.md) | `tests/test_reference.py`, `tests/test_manifests.py` |

## The decisions that go wrong most often

1. **Does the agent's `tools:` grant cover exactly what its body calls?** Leaf roles have no `Agent`, read-only
   roles have no `Edit`/`Write`. `verify-plumbing` (`plugins/stackfoundry/scripts/stackfoundry/plumbing.py`) checks it.
2. **Does the agent get every fact from its brief?** Agents never see the skill's conversation, and agents never
   ask the user: they return `questions` and the dispatching skill asks. Canonical:
   `plugins/stackfoundry/skills/research-stack/SKILL.md` and `plugins/stackfoundry/agents/stack-researcher.md`.
3. **Is it a person-started skill?** Only then `disable-model-invocation: true`; never on a skill that `schedule`
   registers or an agent preloads. Description within the caps (250 skills, 300 agents), no angle brackets.
4. **Does every path resolve inside the plugin?** Reference bundled files through the plugin-root variable in the
   Markdown body (see the rulebook), never reach above the plugin root, never write state under it.
5. **Is this a technology fact?** Then it does not belong in the plugin: it is researched at run time into the
   user's repo. Examples use neutral names (`api`, `desktop`, `web`).

## Non-negotiables

- No technology content and never a real project's internals in a skill, agent or template (`.claude/CLAUDE.md`).
- A release that should reach users bumps `plugin.json` `version`; tags and pushes are the owner's (`docs/release.md`).
- Never show an agent the `fixtures/*/EXPECTED.md` answer keys; never "fix" a fixture.
- Generated code: none in this repo.

## Working procedure

1. Read the rulebooks for the files you are about to touch, and `docs/design.md` before an architecture change.
2. **Read a neighbour first**: the closest existing skill or agent, and match its sections (`## Tooling` last),
   wording and length.
3. Make the change. A renamed or new CLI call: check the subcommand exists in `plugins/stackfoundry/scripts/stackfoundry/cli.py`. A
   template change: bump its `templateVersion`. A user-visible change: `plugins/stackfoundry/CHANGELOG.md`.
4. Verify with the target's gate: `python -m unittest discover -s tests -t . -v`,
   `sh plugins/stackfoundry/scripts/stackfoundry.sh verify-plumbing plugins/stackfoundry`,
   `claude plugin validate --strict .`, `claude plugin validate --strict plugins/stackfoundry`. Evals cost tokens:
   ask before `claude plugin eval`.
5. Then `/stackfoundry:review-changes` for an independent review.

## Tooling
- `Read` the rulebooks and a neighbour, `Edit`/`Write` the change, `Bash` for the gate.
