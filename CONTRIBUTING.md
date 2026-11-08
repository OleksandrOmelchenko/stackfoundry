# Contributing

## Ground rules

1. **Procedure in the plugin, facts in the repo.** A skill or agent says *how* to do a job. Everything about a
   particular codebase (targets, paths, gate commands, harnesses, conventions) comes from the repo profile that
   `init` writes. Never write a technology's rules into the plugin: they are researched at run time and cited.
2. **One file is the whole truth.** A rule lives in one place and everything else links to it. A copy drifts.
3. **No volatile facts in living text.** No counts of code things, `file:line`, "as of" dates, SHAs or measured
   durations in skills, agents, rulebooks or docs. Write the rule, or the command that finds the fact.
4. **Every generator has an adversarial checker.** A new role that writes or fixes something comes with the role that
   tries to refute it.

The detailed authoring rules are in [`.claude/rules/authoring.md`](.claude/rules/authoring.md). Claude Code loads
them when you edit anything under `plugins/`.

## Setup

```sh
git config core.hooksPath .githooks
```

The pre-commit hook runs the unit tests, the plumbing check and (when `claude` is on `PATH`) manifest validation.

## Checks

```sh
python -m unittest discover -s tests -t .
sh plugins/stackfoundry/bin/stackfoundry verify-plumbing plugins/stackfoundry
claude plugin validate --strict .
claude plugin validate --strict plugins/stackfoundry
claude plugin details stackfoundry --plugin-dir plugins/stackfoundry   # projected token cost of the listing
```

## Evals

Evals live in `plugins/stackfoundry/evals/<case>/` and run against the fixture repos that
`fixtures/<name>/scaffold.py` builds:

```sh
claude plugin eval plugins/stackfoundry --scaffold --case "init-*"
```

Each case runs in fresh `claude -p` sessions with and without the plugin, so it spends real tokens. Run the cases for
what you changed and say in the PR which ones you did not run.

## Releasing

See [docs/release.md](docs/release.md).
