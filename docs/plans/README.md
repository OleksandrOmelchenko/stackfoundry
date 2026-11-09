# Plans: the backlog

Future, not-yet-started features, one file each, unordered. `/stackfoundry:plan-feature` creates one from
[`_template.md`](_template.md); `/stackfoundry:implement-plan` builds one and retires it into
`../specifications/`; `/stackfoundry:retire-plan` reconciles one built outside that flow;
`/stackfoundry:backlog` lists what is open.

## Categories

Line 3 of every plan and spec is `**Category:** <word>`, one of:

- `cli`: the helper CLI, its launcher and the guard hook (`plugins/stackfoundry/scripts/`, `hooks/`).
- `plugin`: skills, agents, the reference method and evals (`plugins/stackfoundry/`).
- `repo`: CI, release, contributor tooling and repo-level docs (`.github/`, `.githooks/`, `docs/`).

## Deferred upgrades

[`deferred-upgrades.md`](deferred-upgrades.md) holds majors that were declined or blocked, with the check that
unblocks each.
