# Target `cli`

<!-- Facts every role agent needs for this target. Grounded: every line names a path + symbol or a command that
     init ran. No counts, no file:line. Owned by the team; /stackfoundry:sync proposes changes, never overwrites. -->

The stackfoundry helper CLI, its POSIX sh launcher and the guard hook wiring. Exposure: offline (runs locally in
plugin users' sessions, reads their untrusted repo content and hook JSON on stdin). Stakes: safety (the guard is the
enforcement point and fails open), data integrity (writes `manifest.lock.json` and rendered rulebooks in users' repos).

## Stack

| Layer | Pack | Rulebook |
|---|---|---|
| language | `language-python` | `.claude/rules/language-python.md` |
| language | `language-posix-sh` | `.claude/rules/language-posix-sh.md` |
| app-model | `app-model-python-cli` | `.claude/rules/app-model-python-cli.md` |
| tooling | `tooling-unittest` | `.claude/rules/tooling-unittest.md` |
| tooling | `tooling-github-actions` | `.claude/rules/tooling-github-actions.md` |

## Where things are

- Source: `plugins/stackfoundry/scripts/**`, `plugins/stackfoundry/bin/**`, `plugins/stackfoundry/hooks/**`.
  Entry point: `plugins/stackfoundry/scripts/stackfoundry.sh` (finds Python >= 3.11, runs `python -I`) →
  `plugins/stackfoundry/scripts/stackfoundry/cli.py` `build()` / `main()`. Hook entry: `plugins/stackfoundry/hooks/hooks.json` PreToolUse →
  `stackfoundry guard` → `plugins/stackfoundry/scripts/stackfoundry/guard.py` `main()` / `decide()`.
- Tests: `tests/test_*.py` (all but `test_reference.py` and `test_manifests.py`), stdlib `unittest`; harness
  `tests/_support.py` (`TempRepo`, `write`, `git`, `run_cli`, `targets_json`, `HAS_GIT`). `fixtures/**` is test
  data read by `tests/test_fixtures.py`: never product code, never "fixed".
- Generated, never hand-edited: none.

## Gate

```sh
python -m unittest discover -s tests -t . -v
sh plugins/stackfoundry/scripts/stackfoundry.sh verify-plumbing plugins/stackfoundry
```

Preconditions: Python >= 3.11 on PATH as `python3`, `python` or `py -3`; git on PATH (git-dependent tests skip
without it via `tests/_support.py` `HAS_GIT`; tests that need `sh` skip without it).
Shuffled run (assurance gate): none yet (stdlib `unittest` has no shuffle; open question in
`.claude/rules/tooling-unittest.md`). Coverage: none yet. Mutation lane: none yet: /stackfoundry:setup-mutation.

Local URL for live repros: not served locally.

## Oracle sources

In precedence order: `docs/design.md` and `docs/specifications/` (when present), the rulebooks in `.claude/rules/`,
the JSON schemas in `plugins/stackfoundry/reference/schemas/`, the subcommand help strings in
`plugins/stackfoundry/scripts/stackfoundry/cli.py` `build()` (each says whether it writes), the Claude Code hooks contract cited in
`.claude/rules/app-model-python-cli.md`, bug reports under `docs/bug-reports/`.

## Emphasis

Offline CLI that guards other people's sessions: fail-open behaviour of the guard (a usage error, an exception or a
timeout must never block every tool call, and a bad `guards.json` must never allow more than it should), read-only
subcommands that must never write, path handling for arbitrary repos (spaces, non-ASCII, Windows separators),
defensive parsing of untrusted JSON and repo files, cross-platform behaviour on the three CI operating systems.

## Traps

- `guard.py` `decide()` returns a command entry's `decision` as written in `guards.json`; only `guard --check`
  (`check_file()`) rejects values other than `deny`/`ask`, and the hook never runs that check
  (`.claude/rules/app-model-python-cli.md`).
- The Python floor appears in code (`plugins/stackfoundry/scripts/stackfoundry.sh`, `.githooks/pre-commit`, CI matrix) and in prose; they move
  together (`.stackfoundry/ecosystems.json` `python-platform`).
