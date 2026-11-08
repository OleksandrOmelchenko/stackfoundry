---
description: Documentation rules for this repo's docs and READMEs.
paths:
  - "docs/**"
  - "**/README.md"
  - "**/CHANGELOG.md"
  - "CONTRIBUTING.md"
---

# Documentation

- **Write what stays true.** No counts of skills, agents or tests, no `file:line`, no "as of" dates in living docs.
  Name the folder or the command that finds the fact (`ls plugins/stackfoundry/skills`).
- **One home per fact.** The architecture is in `docs/design.md`; the release procedure in `docs/release.md`;
  authoring rules in `.claude/rules/authoring.md`. Others link.
- `plugins/stackfoundry/CHANGELOG.md` is a snapshot per version: record under `Unreleased` in the change that makes it true.
- The plugin's own `reference/rulebooks/documentation.md` is the rulebook stackfoundry installs into user repos.
  This file governs this repo's docs only.
