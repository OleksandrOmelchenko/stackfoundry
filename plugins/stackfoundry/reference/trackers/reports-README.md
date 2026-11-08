---
templateVersion: 1
output: "{{docsRoot}}/{{folder}}/README.md (folder: dependency-reports | radar | performance-reports | reports)"
---
# {{Folder title}}

Dated, read-only snapshots written by {{the skill: check-updates (dependency-reports) | tech-radar,
stackfoundry-radar (radar) | performance-review, run-benchmarks (performance-reports) | flaky-watch, report-only
docs-reconciler (reports)}}. A report is never edited after it is written: acting on it (`{{act-on-updates | act-on-radar}}`)
records results in the trackers and plans it touches, and the next report reflects them.

Naming: `YYYY-MM-DD-<slug>.md`, dated in the profile's time zone. A second run on the same day overwrites that
day's file.

## Index

| Report | Summary |
|---|---|
