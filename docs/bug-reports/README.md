# Bug reports

Findings from `/stackfoundry:bug-hunt`, `/stackfoundry:review-changes`, `/stackfoundry:quality-sweep`,
`/stackfoundry:fix-tests` (product defects) and `/stackfoundry:debug`. Each report is a dated snapshot whose
findings are a **tracker**: the marker on each finding is kept current by the skill that fixes or verifies it.

## Naming

`YYYY-MM-DD-<target or slug>-<mode>.md`, e.g. `2026-01-15-api-deep-sweep.md`, `2026-01-16-checkout-diff.md`.

## A finding

```markdown
### B3 🟡 ⬜ OPEN — <short title>
- **Where:** `path/to/file.ext:123` (the anchor of the moment; a symbol name too)
- **Category:** <the pack's bug category>
- **Failure:** <the concrete input, state or sequence and the wrong outcome>
- **Fix:** <the suggested change>
```

- **Ids** are stable (`B1`, `B2`, …; a prefix per report family is fine) and never reused. A re-found finding keeps
  its id.
- **Severity**: 🔴 blocker (wrong, unsafe, or breaks something outside the change) · 🟡 confirm · 🔵 suggestion.
- **Markers**: ⬜ OPEN · ⚠️ PARTIAL (the remainder spelled out) · ✅ FIXED · 🚫 WONT-FIX (with the reason).
  `/stackfoundry:fix-verify` flips them from its verdicts; nobody else flips a marker without verification.

## The banner

Line under the title: `**Open:** 🔴 B1 · 🟡 B3, B4`, or `**Open:** none`. Open ids by severity, never a tally.
`stackfoundry tracker check <file>` verifies it.

## Index

| Report | State | Open |
|---|---|---|
