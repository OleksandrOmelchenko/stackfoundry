# stackfoundry repository

This repo is a Claude Code **marketplace** (`.claude-plugin/marketplace.json`) with one plugin,
`plugins/stackfoundry/`. The plugin generates, for any repository, a grounded set of rulebooks and target profiles
that drive generic role agents and orchestrator skills. Read [`docs/design.md`](../docs/design.md) before changing
the architecture.

## Layout

- `plugins/stackfoundry/skills/<name>/SKILL.md`: skills. `agents/<name>.md`: generic role agents.
- `plugins/stackfoundry/reference/`: the method (layers, schemas, research procedure, role briefs, rulebook and
  tracker templates). Skills read it through `${CLAUDE_PLUGIN_ROOT}/reference/…`.
- `plugins/stackfoundry/bin/stackfoundry` + `scripts/stackfoundry/`: the helper CLI (Python 3.10+, standard library
  only, no network). `hooks/hooks.json`: the guard hooks.
- `plugins/stackfoundry/evals/`: `claude plugin eval` cases. `fixtures/`: scaffold scripts for eval repos.
- `tests/`: unittest suite. `docs/`: design and release notes.

## Non-negotiables

- **No technology content in the plugin.** Rules about a framework are researched at run time and cited in the
  user's repo. The plugin ships procedure and templates only.
- **Never name a real project's internals** in a skill, agent or template. Examples use neutral names
  (`api`, `desktop`, `web`) or placeholders.
- **Python helpers: standard library only, no network calls, JSON for data.** Every subcommand documents whether
  it writes, and the read-only ones never do.
- Authoring rules for skills and agents: [`.claude/rules/authoring.md`](rules/authoring.md). Documentation rules:
  [`.claude/rules/documentation.md`](rules/documentation.md).

## Checks before calling a change done

```sh
python -m unittest discover -s tests -t .
sh plugins/stackfoundry/bin/stackfoundry verify-plumbing plugins/stackfoundry
claude plugin validate --strict .
claude plugin validate --strict plugins/stackfoundry
```

## Git

Single branch: work on `main`. Release tags (`stackfoundry--v<version>`) and pushes are the owner's. The pre-commit
hook lives in `.githooks/` (`git config core.hooksPath .githooks`).
