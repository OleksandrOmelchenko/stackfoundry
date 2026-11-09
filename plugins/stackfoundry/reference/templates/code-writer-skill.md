---
templateVersion: 3
output: <each skills folder `stackfoundry outputs` lists>/{{app-model}}-code-writer/SKILL.md; the filled description is at most 250 characters (verify-plumbing counts characters, not bytes), and every path in the body is written from the repo root (`plugins/x/hooks/hooks.json`, never `hooks/hooks.json`), links relative to the skill's own folder
---
---
name: {{app-model}}-code-writer
description: Write or change {{app-model title}} code the repo's way, in {{the target names, as "the cli target" or "the api and web targets"}} — {{the three or four decisions that go wrong most often, in a few words}}. Use when editing {{typical files}}.
---

# {{app-model title}} code writer

Write code that looks like the code already here. The rules live in the rulebooks below, which are authoritative;
this skill is the decision procedure. Read them before editing.

| Read first | Before touching |
|---|---|
{{one row per pack in these targets' stacks: rulebook link | what it governs}}

## The decisions that go wrong most often

{{three to six numbered decisions, each: the question to ask, the answer here, the consequence of the wrong
answer, and the path + symbol of the canonical example in this repo. Drawn from the packs' rules, ordered by
consequence.}}

## Non-negotiables

- Generated code is never hand-edited: {{globs → how to regenerate}}.
- {{other repo-wide guardrails from the profile that bite in this app model}}

## Working procedure

1. Read the rulebooks for the files you are about to touch.
2. **Read a neighbour first**: the closest existing {{unit kind}} and match its shape, naming and comment density.
3. Make the change. {{schema / contract / generated-client follow-ups and the skill or command for each}}
4. Verify with the target's gate: {{gate commands per target}}.
5. Then `/stackfoundry:review-changes` for an independent review.

## Tooling
- `Read` the rulebooks and a neighbour, `Edit`/`Write` the change, `Bash` for the gate.
- {{tool notes specific to this app model, e.g. stop a running service before building}}
