---
templateVersion: 3
output: .stackfoundry/targets/{{target}}.md
---
# Target `{{target}}`

<!-- Facts every role agent needs for this target. Grounded: every line names a path + symbol or a command that
     init ran. No counts, no file:line. Owned by the team; /stackfoundry:sync proposes changes, never overwrites.
     The Stack and Gate sections between markers are rendered by `stackfoundry render-target` from targets.json and
     gates.json: change those files and re-render, never edit inside the markers. -->

{{one line: what it is, who reaches it (exposure), what is at stake}}

## Stack

<!-- stackfoundry:begin target-stack (rendered by stackfoundry render-target; edit outside the markers) -->
{{rendered by stackfoundry render-target}}
<!-- stackfoundry:end -->

## Where things are

- Source: {{globs}}. Entry point: {{path + symbol}}.
- Tests: {{globs}}, {{framework}}; harness {{base classes, fixtures, factories, providers: path + symbol}}.
- Generated, never hand-edited: {{globs and how each is regenerated}}.

## Gate

<!-- stackfoundry:begin target-gate (rendered by stackfoundry render-target; edit outside the markers) -->
{{rendered by stackfoundry render-target}}
<!-- stackfoundry:end -->

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
