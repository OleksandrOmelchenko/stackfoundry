# Target `plugin`

<!-- Facts every role agent needs for this target. Grounded: every line names a path + symbol or a command that
     init ran. No counts, no file:line. Owned by the team; /stackfoundry:sync proposes changes, never overwrites. -->

The Claude Code plugin and its marketplace entry: skills, generic role agents, the reference method and eval cases.
Exposure: offline (published on a public GitHub marketplace; runs inside users' local sessions and reads their
untrusted repos). Stakes: safety (its skills write the `guards.json` the hook enforces), data integrity (skills write
rulebooks, trackers and code into users' repos).

## Stack

<!-- stackfoundry:begin target-stack (rendered by stackfoundry render-target; edit outside the markers) -->
| Layer | Pack | Rulebook |
|---|---|---|
| app-model | `app-model-claude-code-plugin` | [app-model-claude-code-plugin](../rules/app-model-claude-code-plugin.md) |
| capability | `capability-claude-code-marketplace` | [capability-claude-code-marketplace](../rules/capability-claude-code-marketplace.md) |
| tooling | `tooling-claude-plugin-eval` | [tooling-claude-plugin-eval](../rules/tooling-claude-plugin-eval.md) |
| tooling | `tooling-unittest` | [tooling-unittest](../rules/tooling-unittest.md) |
<!-- stackfoundry:end -->

## Where things are

- Source: `plugins/stackfoundry/skills/**` (`<name>/SKILL.md`), `agents/**` (`<name>.md`), `reference/**`
  (layers, schemas, templates, rulebooks, trackers), `evals/**`, `plugins/stackfoundry/.claude-plugin/plugin.json`,
  root `.claude-plugin/marketplace.json`. Entry point: `plugin.json` (name, version, `userConfig`).
- Authoring rules: `.stackfoundry/rules/authoring.md`; design: `docs/design.md`.
- Tests: `tests/test_reference.py`, `tests/test_manifests.py`, `tests/test_build_clients.py` (stdlib `unittest`, harness `tests/_support.py`);
  `verify-plumbing` (`plugins/stackfoundry/scripts/stackfoundry/plumbing.py`); eval cases in `plugins/stackfoundry/evals/<case>/` scaffolded
  from `fixtures/` by `fixtures/scaffold-lib.sh`. `fixtures/*/EXPECTED.md` are answer keys: never show them to an agent.
- Generated, never hand-edited: the other assistants' plugin files, written by `scripts/build_clients.py` (the
  globs are `targets.json` `generated`, guarded by `guards.json`). Change the source and regenerate.

## Gate

<!-- stackfoundry:begin target-gate (rendered by stackfoundry render-target; edit outside the markers) -->
```sh
python -m unittest discover -s tests -t . -v
sh plugins/stackfoundry/scripts/stackfoundry.sh verify-plumbing plugins/stackfoundry
claude plugin validate --strict .
claude plugin validate --strict plugins/stackfoundry
```

Status:
- `python -m unittest discover -s tests -t . -v`: proven
- `sh plugins/stackfoundry/scripts/stackfoundry.sh verify-plumbing plugins/stackfoundry`: proven
- `claude plugin validate --strict .`: proven
- `claude plugin validate --strict plugins/stackfoundry`: proven

Preconditions: Python >= 3.11 on PATH; the claude CLI on PATH (CI pins @anthropic-ai/claude-code in
.github/workflows/ci.yml).

Suites:
- reference-and-manifests (unit): `python -m unittest tests.test_reference tests.test_manifests -v` (proven);
  shuffled run: none recorded; coverage: none recorded; mutation: none yet (/stackfoundry:setup-mutation).
- plumbing (contract): `sh plugins/stackfoundry/scripts/stackfoundry.sh verify-plumbing plugins/stackfoundry`
  (proven); shuffled run: none recorded; coverage: none recorded; mutation: none yet (/stackfoundry:setup-mutation).
- evals (e2e): `cd plugins/stackfoundry && claude plugin eval . --scaffold --runs 1 --no-publish --tag read-only`
  (unproven); shuffled run: none recorded; coverage: none recorded; mutation: none yet
  (/stackfoundry:setup-mutation).

Local URL for live repros: not served locally.
<!-- stackfoundry:end -->

The evals suite is not a gate: it spends real tokens and needs an OS sandbox for Bash cases (none on native
Windows), so it is ask-guarded and stays unproven until someone runs it on purpose.

## Oracle sources

In precedence order: `docs/design.md` and `docs/specifications/` (when present), the rulebooks in `.stackfoundry/rules/`
(including `authoring.md`), the official Claude Code docs cited in the plugin packs, the schemas in
`plugins/stackfoundry/reference/schemas/`, `docs/release.md`, bug reports under `docs/bug-reports/`.

## Emphasis

Procedure that other people's agents follow in their repos: instructions that are wrong, unclear or contradict the
CLI; tool grants that do not cover the body (or grant writes to a read-only role); untrusted repo or web content
treated as instructions; writes outside what a skill announces; technology content or real project internals
leaking into the plugin; path references that do not resolve under `${CLAUDE_PLUGIN_ROOT}`.

## Traps

- The marketplace entry may carry a `version`; `tests/test_manifests.py` only requires it to equal `plugin.json`
  (`.stackfoundry/rules/capability-claude-code-marketplace.md`).
- `guard-blocks-generated-edit` can pass without Edit/Write allowed, proving nothing
  (`.stackfoundry/rules/tooling-claude-plugin-eval.md`).
