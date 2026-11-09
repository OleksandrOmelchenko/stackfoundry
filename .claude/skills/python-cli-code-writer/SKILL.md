---
name: python-cli-code-writer
description: Write or change the stackfoundry helper CLI the repo's way — stdlib only, explicit encodings, atomic writes, exit codes 0/1/2, a guard that fails open. Use when editing the plugin's scripts, bin or hooks.
---

# Python CLI code writer

Write code that looks like the code already here. The rules live in the rulebooks below, which are authoritative;
this skill is the decision procedure. Read them before editing.

| Read first | Before touching |
|---|---|
| [`language-python`](../../rules/language-python.md) | any `.py` file: encodings, 3.11 floor, subprocess, paths |
| [`language-posix-sh`](../../rules/language-posix-sh.md) | `plugins/stackfoundry/scripts/stackfoundry.sh`, `.githooks/pre-commit`, `*.sh` |
| [`app-model-python-cli`](../../rules/app-model-python-cli.md) | `scripts/stackfoundry/*.py`, `plugins/stackfoundry/hooks/hooks.json`: subcommands, the guard's hook contract |
| [`tooling-unittest`](../../rules/tooling-unittest.md) | `tests/**` |
| [`tooling-github-actions`](../../rules/tooling-github-actions.md) | `.github/**` |

## The decisions that go wrong most often

1. **Can this path block the session?** On the hook path (`guard` without `--check`) every outcome exits 0, and
   only `deny` or `ask` is ever emitted; a crash, a usage error or a bad `guards.json` must mean "no opinion", never
   a deny of every tool call and never an `allow`. Canonical: `plugins/stackfoundry/scripts/stackfoundry/guard.py` `main`, `decide`,
   `_decision`.
2. **Does this subcommand write?** Only documented writers write, through a temp file in the destination folder
   and `os.replace`; read-only ones open nothing for writing. Canonical: `plugins/stackfoundry/scripts/stackfoundry/manifest.py`
   `write_json`. Its help in `cli.py` `build()` starts with `(read-only)` or names what it writes.
3. **Which encoding, which newline?** Always explicit: `utf-8` for what this code writes (with `newline="\n"`),
   `utf-8-sig` for JSON read from a user repo, stdin read as bytes. The 3.11 Windows CI job is the only one that
   catches an omission. Canonical: `guard.py` `main`, `survey.py` `_read`.
4. **Does it run on 3.11, Windows, macOS and Linux?** No API newer than 3.11; paths turned to forward slashes
   before globbing, hashing or JSON; external programs by absolute path with an argv list (`gitutil.py`
   `git_exe`, `run`). Untrusted values passed to git get `--end-of-options`.
5. **What does the exit code say?** 0 = clean, 1 = found something, 2 = could not run (`cli.py` `main`). A crash
   must not read as a verdict.

## Non-negotiables

- Standard library only, no network calls, JSON for data (`.claude/CLAUDE.md`).
- No technology content and no real project's internals in the plugin.
- Generated code: none in this repo.

## Working procedure

1. Read the rulebooks for the files you are about to touch.
2. **Read a neighbour first**: the closest existing subcommand module and its test module, and match their shape,
   naming and comment density.
3. Make the change. A new or changed subcommand: update `cli.py` `build()` help and the module docstring, the
   skill or agent that calls it, and add a test in `tests/` using `tests/_support.py` (`TempRepo`, `run_cli`).
4. Verify with the target's gate: `python -m unittest discover -s tests -t . -v` and
   `sh plugins/stackfoundry/scripts/stackfoundry.sh verify-plumbing plugins/stackfoundry`.
5. Then `/stackfoundry:review-changes` for an independent review.

## Tooling
- `Read` the rulebooks and a neighbour, `Edit`/`Write` the change, `Bash` for the gate.
