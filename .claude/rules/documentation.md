---
description: Documentation rulebook — write what stays true. Living vs snapshot vs tracker docs, what not to write (counts, file:line, dates, SHAs, versions as background), always-loaded files stay small, and the plans → specifications lifecycle.
paths:
  - "docs/**"
  - ".claude/**"
  - "**/CLAUDE.md"
  - "**/README.md"
---

# Documentation rulebook: write what stays true

A line earns its place if a reader would **do something different** without it. A number that only describes
today's code fails that test and costs a sync every time the code moves; more often nobody syncs it and it starts
lying. `stackfoundry volatile-facts <path>` reports the mechanical cases; every hit still needs judgment.

## Living, snapshot, tracker

| Kind | Where | Rule |
|---|---|---|
| **Living**: must stay true | specs, plans, READMEs, `.claude/rules/`, `CLAUDE.md` files, skills, agents | everything here applies |
| **Snapshot**: records a moment | dated reports under `docs/` (bug reports, dependency, radar, performance) | counts and `file:line` are fine as that moment's anchor; never re-synced, except the anchor of a finding still open |
| **Tracker**: per-row status | test designs; the findings of a bug report | status lives on each row; the summary lists **open ids**, never tallies |

## Don't write → write instead

| Don't write | Write instead |
|---|---|
| Suite sizes, pass counts | The fact that matters: "the suite is green, so any red is a regression" |
| Counts of code things | The discovery command or anchor that finds them |
| `file:line` in living text | Path + symbol: `OrdersService.Apply`, `path::TestName`, `doc §section` |
| Measured durations | The qualitative cost the reader acts on: "runs a full production build; run it once, last" |
| Current versions as background | Nothing: the manifest is the source. A version only with the rule that depends on it and why |
| "As of <date>", "since", "used to", SHAs | The current rule. History belongs in a spec's Why |
| Inventories that copy the code | The principle plus a pointer to the folder |
| Struck-through finished follow-ups | Delete them |
| A tally in a tracker summary | Open ids: `**Open:** TD-3, TD-7 · **Questions:** Q1`; `**Open:** 🔴 B2 · 🟡 B5` |

## Keep

- Enforced contracts: ports, exit codes, caps and limits, timeouts.
- A configured value with its constant's name, so it can be found and checked.
- A version with its reason or unblock condition.
- Decision-sizing numbers inside a spec's Why.
- `file:line` in snapshot findings and in an agent's ephemeral output.

## Always-loaded files stay small

The root `CLAUDE.md`, every rule without `paths:` and every skill and agent description cost context in every
session. `CLAUDE.md` holds repo-wide guidance only, with no listing of skills or agents (Claude discovers them by
their description). Area rules go in a path-scoped rulebook.

## Plans, specifications and the backlog

- **`docs/plans/`**: future, not-yet-started features, one file each (`/stackfoundry:plan-feature`),
  **deleted** once implemented.
- **`docs/specifications/`**: living specs of built features, each with a Status and
  **Follow-ups (not yet implemented)**.
- Every plan and spec carries `**Category:**` on line 3 (the vocabulary is in `docs/plans/README.md`).
- "What's pending?" → `/stackfoundry:backlog`.
- Implementing a plan retires it in the same change: delete the plan, record the spec and its README row, sync
  affected instructions (`/stackfoundry:implement-plan`).
- Completing a follow-up updates its spec in the same change.

## A spec's Verification

States **what was exercised** and that the gate was green. No suite totals.
