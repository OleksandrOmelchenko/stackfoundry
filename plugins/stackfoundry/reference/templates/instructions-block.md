---
templateVersion: 6
output: each instruction file `stackfoundry outputs` lists (CLAUDE.md, AGENTS.md, GEMINI.md), between the stackfoundry markers; filled only by `stackfoundry render-block`
---
<!-- stackfoundry:begin (managed by the stackfoundry init and upgrade skills; edit outside the markers) -->
## stackfoundry

This repo's stackfoundry profile is in `.stackfoundry/`: start at `profile.md`; targets and gates are in
`targets.json`, settings in `config.json`.

{{rulebooks}}

Targets: {{target names}}. Say "customize <skill>" to change what a stackfoundry skill or agent does here; the
change lives in `.stackfoundry/extensions/`.
<!-- stackfoundry:end -->
