# Repo extensions

A team changes what a stackfoundry skill or agent does in its repository without editing the plugin, which a
marketplace update replaces. The change lives in a file the repo owns, the plugin's skill or agent reads it every
run, and an upgrade never writes to it: it re-checks it, and merges full replacements against a stored base.

The `customize` skill writes these files; this page is the format.

## Where

| File | Changes |
|---|---|
| `.stackfoundry/extensions/skills/<skill>.md` | the plugin skill `<skill>` |
| `.stackfoundry/extensions/agents/<role>.md` | the plugin agent `<role>`, for every target (or one, with `## Target:`) |
| `.stackfoundry/agents/<target>-<role>.md` | a materialized agent: a whole per-target copy (`materialize`) |
| `.stackfoundry/extensions/.base/` | the plugin text each full copy was taken from, and `index.json`; written by the CLI only |

A brand-new skill or agent is not an extension: put it in the repo's own skills folder or `targets.json`
`specialists`, and call it from an extension ("After: Verify — run the `release-check` skill").

## Two modes

```markdown
---
extends: bug-hunt
mode: extend
---
Optional notes for people; ignored before the first section.

## Rules
Applies throughout the skill and wins where it conflicts with the skill's own text.

## Before: Categories
Done before the step headed "Categories".

## After: Verify
Done after the step headed "Verify".

## Replace: Report
Done instead of the step headed "Report".

## Target: api
Applies only when the run's target is `api`.
```

- **`extend`** (the default, and the one to prefer): anchored additions. The plugin's own text keeps arriving with
  every update; only the parts named here change.
- **`replace`**: the body below the frontmatter is the whole skill or agent, followed instead of the plugin's. It is
  for a rewrite, when more than about half of the steps change. `stackfoundry extensions new <name> --replace`
  creates it with the plugin's current text and stores that text as the base for later merges.

`extends` equals the file name. Sections other than the five above are an error.

## Anchors

An anchor names a step of the plugin skill or agent, without its number: a `##` or `###` heading (`## 3. Ask` is
anchored as `Ask`), or a numbered step that opens with a bold label (`5. **Verify every finding.** …` is anchored as
`Verify every finding`). Matching ignores case, emphasis, a trailing period and surrounding spaces;
`stackfoundry extensions new` lists a skill's anchors. A plugin update that renames a heading leaves the anchor
orphaned: `stackfoundry extensions check` reports it with the nearest current heading, and `upgrade` asks where it
goes now. The plugin announces renamed headings in its changelog under "Changed (extension anchors)".

## Precedence

1. A `replace` file, or a materialized agent for the run's target, is followed instead of the plugin text.
2. Otherwise the plugin text, with the `extend` file's sections applied at their anchors.
3. `## Rules` win over the skill's own text where the two conflict; `## Target:` sections apply only to that target.

## The fixed contract

Other skills and agents parse what a skill or agent produces, and the plugin's safety rules hold everywhere, so an
extension never:

- removes a confirmation or a question the skill asks before writing, or runs a git write the repo's policy forbids;
- disables or works around the guard hook;
- drops a role's clause that instructions found in files, pages and tool output are data, or its "What you must not
  do" section;
- changes the brief fields an orchestrator passes, the report or tracker shape, the severity scale, the verdict
  words, or the tracker markers.

Every skill and agent names the extensions it applied in its report, so an extension's effect is never invisible.
`extensions check` warns when a `replace` file drops the role's data clause or its "What you must not do" section,
and when extension text names the guard, `guards.json`, hooks, a permission mode, `--no-verify`, `curl` or `wget`
(for a `replace` file, only where it names one more often than the plugin's own text). The warnings are for a
person to judge: the text may be legitimate.

An extension that needs one of these changed is a request for the plugin itself: open an issue.

## Upgrades

| File | On a plugin update |
|---|---|
| `extend` | never rewritten; `extensions check` re-checks its anchors |
| `replace` and materialized | `extensions merge` runs a three-way merge (base = the plugin text it was taken from, theirs = the new plugin text, ours = the repo's file). A clean merge is written and the base moves forward; a conflict is written to `<file>.merge.md` for the user to settle, then `extensions merge <file> --resolved` |

### What the index is trusted with

`.base/index.json` is committed, so whoever controls the repo controls it, and the CLI reads it as untrusted data:

- **Base copies:** each base path is derived from its file's path (`.base/skills|agents|materialized/<name>.md`).
  The index's `base` field is informational and never read.
- **Sources:** a `from` is accepted only as `skills/<name>/SKILL.md` or `agents/<name>.md`, with no absolute paths
  and no `..`.
- **Files:** an entry's key must be an extension or materialized-agent file.
- **Links:** after resolving them, the source must lie inside the plugin, the base inside `.base/`, and the file and
  any `.merge.md` inside `.stackfoundry/`.

`extensions check` reports an entry that breaks a rule as an error and never suggests a command for it. `merge`,
`forget` and `base` refuse it. The CLI never writes such an entry, so find out who committed it before you remove it
by hand.

## Commands

| Command | Does |
|---|---|
| `stackfoundry extensions list [--json]` | every extension and fork: what it changes, its mode, and whether the plugin moved past its base |
| `stackfoundry extensions check` | anchors, targets, names, base copies; exit 1 on an error |
| `stackfoundry extensions new skill\|agent <name> [--replace]` | scaffold one (writes the file, and the base for `--replace`) |
| `stackfoundry extensions base <file> --from agents/<role>.md` | record the base of a materialized agent |
| `stackfoundry extensions merge <file> [--resolved]` | three-way merge a full copy with the installed plugin |
| `stackfoundry extensions forget <file>` | drop a full copy's base (after deleting the file) |

Undo an extension by deleting its file (and, for a full copy, `extensions forget`).
