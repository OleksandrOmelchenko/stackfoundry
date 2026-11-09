---
templateVersion: 1
output: .stackfoundry/targets/{{target}}.md
---
# Target `{{target}}`

<!-- Facts every role agent needs for this target. Grounded: every line names a path + symbol or a command that
     init ran. No counts, no file:line. Owned by the team; /stackfoundry:sync proposes changes, never overwrites. -->

{{one line: what it is, who reaches it (exposure), what is at stake}}

## Stack

| Layer | Pack | Rulebook |
|---|---|---|
{{one row per pack: layer | pack id | .stackfoundry/rules/<pack-id>.md}}

## Where things are

- Source: {{globs}}. Entry point: {{path + symbol}}.
- Tests: {{globs}}, {{framework}}; harness {{base classes, fixtures, factories, providers: path + symbol}}.
- Generated, never hand-edited: {{globs and how each is regenerated}}.

## Gate

```sh
{{build}}
{{test}}
{{lint}}
```

Preconditions: {{e.g. services that lock build output must be stopped; a container runtime; a built artifact}}.
Shuffled run (assurance gate): `{{shuffle command}}`. Coverage: `{{coverage command}}`. Mutation lane:
{{command, or "none yet: /stackfoundry:setup-mutation"}}.

Local URL for live repros: {{localUrl, or "not served locally"}}.

## Benchmarks

{{only on a benchmark project's target: kind (micro | load), harness pack, build / dry-run / measured-run / compare
commands, the read-only preflight, the results folder, and for load benchmarks the disposable target they run against}}

## Oracle sources

Where an expected value may come from for this target, in precedence order: {{specs folder, rulebooks, generated
contracts (API schema, client models, error types, enums), declared contracts in code, bug reports}}.

## Emphasis

What a bug hunter, reviewer and test designer weigh first here, given exposure and stakes:
{{e.g. "public and anonymous: input validation, IDOR, caching of personal data"; "staff tool used by several
people at once: lost updates, double submits, conflict surfacing"; "offline CLI: defensive parsing, batch
safety, idempotent reruns"}}

## Traps

{{what has bitten here: each with its evidence (a spec, a bug report id, a config file)}}
