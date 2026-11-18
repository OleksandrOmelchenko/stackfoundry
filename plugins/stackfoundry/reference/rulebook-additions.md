# Repo additions to the shared rulebooks

The shared rulebooks (`testing`, `documentation`, `dependency-bumps`, `benchmarking`) are rendered from the
templates in [`rulebooks/`](rulebooks/) by `stackfoundry render-rulebook <name>`, with the repo's facts filled in
from the profile. A repo that wants its own rules in one of them writes them in an additions file, never in the
rendered rulebook or in an assistant's copy: those are regenerated, and a hand-merged copy has to be merged again on
every plugin update.

## Where

`.stackfoundry/rulebook-additions/<name>.md`, one file per shared rulebook, `<name>` as above. The repo owns it;
`init`, `sync` and `upgrade` never write it.

## Format

```markdown
---
extraPaths:
  - "web/e2e/**"
---

## Oracles: where an expected value may come from

- **Prices come from the price list.** A test's expected price cites `docs/specifications/pricing.md`.

## Determinism

- **The shop's clock.** Use the test clock helper; never the system time.
```

- **`## <heading>`** names a `##` heading of the rendered rulebook. It is matched as extension anchors are
  ([`extensions.md`](extensions.md), Anchors): a leading number, emphasis and case are ignored, so
  `## Oracles: where an expected value may come from` and `## 1. Oracles: …` both match. The section's text is
  appended at the end of that heading's section, after the plugin's own text, in file order.
- **`extraPaths:`** (optional, the only frontmatter key) adds globs to the rulebook's `paths:`, so it also loads for
  those files. Each is a plain glob, as a pack's `rulebookPaths` are: no quotes, commas, braces, `#` or spaces.
- Text before the first `##` section, an unknown frontmatter key, a bad glob or a heading the rulebook does not have
  is an error: `render-rulebook` stops and names the nearest heading. Nothing is dropped silently.

## How it flows

1. `stackfoundry render-rulebook <name> --write` renders the template, fills the profile's facts, then applies the
   additions, into `.stackfoundry/rules/<name>.md`.
2. `stackfoundry render-rule .stackfoundry/rules/<name>.md --client <assistant> --write` writes each assistant's
   copy from that canonical file. The copy is a pure render: the additions reach it through the canonical file.
3. `stackfoundry manifest record` of the rulebook stores the additions file's hash next to the rulebook's;
   `stackfoundry manifest diff` reports the rulebook outdated, with "re-render", when the additions change.
4. On `/stackfoundry:upgrade`, a heading the new template renamed makes `render-rulebook` fail with the nearest
   heading; the user picks where the section goes now, and the plugin's CHANGELOG lists renamed rulebook headings
   under "Changed (extension anchors)".

A rulebook kept as a hand-merged copy (recorded `merged`) moves here once: put the repo's lines in the additions file
under their headings, re-render, and record the rulebook as `generated`.
