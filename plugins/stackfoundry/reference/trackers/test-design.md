---
templateVersion: 1
output: "{{docsRoot}}/test-designs/{{date}}-{{target}}-{{area}}.md"
---
# {{target}}: {{area}} test design

**Open:** {{open TD ids}} · **Questions:** {{open Q ids or "none"}}

Scope: {{area, files, behaviours}}. Oracle sources: {{specs, rulebooks, contracts, bug reports read}}.

| ID | Behaviour (given / when / then) | Technique | Layer | Oracle | Status |
|---|---|---|---|---|---|
{{| TD-1 | … | boundary | unit | `spec.md §2` | ⬜ |}}

## Questions

{{Q1: the expected value no source settles, the rows it blocks, and the options}}

## Already covered

{{behaviours an existing test pins: `path::TestName`}}

## Out of scope

{{what was left out and why}}
