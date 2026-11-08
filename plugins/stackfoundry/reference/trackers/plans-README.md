---
templateVersion: 1
output: "{{docsRoot}}/plans/README.md"
---
# Plans: the backlog

Future, not-yet-started features, one file each, unordered. `/stackfoundry:plan-feature` creates one from
[`_template.md`](_template.md); `/stackfoundry:implement-plan` builds one and retires it into
`../specifications/`; `/stackfoundry:retire-plan` reconciles one built outside that flow;
`/stackfoundry:backlog` lists what is open.

## Categories

Line 3 of every plan and spec is `**Category:** <word>`, one of:

{{the category vocabulary agreed at init, one per line with what it covers}}

## Deferred upgrades

[`deferred-upgrades.md`](deferred-upgrades.md) holds majors that were declined or blocked, with the check that
unblocks each.
