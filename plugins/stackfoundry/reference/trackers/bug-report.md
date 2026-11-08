---
templateVersion: 1
output: "{{docsRoot}}/bug-reports/{{date}}-{{slug}}-{{mode}}.md"
---
# {{target or slug}}: {{mode}} ({{date}})

**Open:** {{open ids by severity, e.g. "🔴 B1 · 🟡 B3, B4", or "none"}}

Scope: {{target(s), files or area, base ref}}. Reviewers: {{agents dispatched, categories}}. Gate: {{commands and
results}}. Not covered: {{what was skipped and why}}.

## Findings

{{one block per finding, 🔴 first:
### B1 🔴 ⬜ OPEN — title
- **Where:** `path:line` (symbol)
- **Category:** …
- **Failure:** …
- **Fix:** …}}

## Clean areas

{{🟢 what was checked and held, specifically}}

## What to fix first

{{two or three lines}}
