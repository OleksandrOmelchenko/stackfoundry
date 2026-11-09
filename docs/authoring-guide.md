# Authoring guide: the contract between skills and agents

The rules for *how* a file is written are in [`.claude/rules/authoring.md`](../.claude/rules/authoring.md). This
guide is the contract that lets skills and agents written separately work together: what an orchestrator hands a
role agent, what the agent reads, what it returns, and the roster of names.

## What every role agent reads, in order

1. `.stackfoundry/profile.md`: the product, users, stakes, constraints, working agreements.
2. `.stackfoundry/targets.json` (its own target's entry) and `.stackfoundry/targets/<target>.md`:
   stack, paths, harness, gate, oracle sources, emphasis, traps.
3. The rulebook of each pack in the target's stack, language first: `.claude/rules/<pack-id>.md`. Its *Bug
   categories*, *Testing*, *Performance* and *Security* sections are where the role's checklist comes from.
4. The shared rulebook of its role: `.claude/rules/testing.md` (test roles), `dependency-bumps.md` (bumpers),
   `documentation.md` (docs roles), `benchmarking.md` (benchmark roles).
5. When the dispatch names a materialized agent for this target (`targets.json` → `materialized`), the
   orchestrator dispatches that one instead, and the generic agent is not involved.

A missing profile file is reported in one line ("no `.stackfoundry/targets.json`: run
`/stackfoundry:init`") and the agent stops. It never invents the facts the profile would hold.

## What the orchestrator passes (the dispatch brief)

Every `Agent` call to a role agent carries these fields, as plain labelled lines at the top of the prompt:

```text
target: api                         # absent for cross-target roles (change-reviewer, docs roles)
scope: files: a.cs, b.cs | area: src/Api/Orders | diff: main...HEAD | design: docs/test-designs/x.md
category: concurrency               # bug-hunter: exactly one category per invocation (absent = all, Emphasis first)
mode: <see the table below>
exposure: public                    # optional; security roles: copied from targets.json
stakes: money, pii                  # optional; security roles: copied from targets.json
prior: <the still-relevant findings / design rows / verdicts, quoted>
gate: <the central gate's result, when the orchestrator ran it>
concurrency: read-only, do not build | you are the only builder now | run tests --no-build only
session: <environment facts: the running app's URL for a live repro (else the target's localUrl), a session id a script needs>
output: <the one file a writing role may write, when it writes a single artefact (stack-researcher: its pack.json)>
```

| `mode` | Used by | Meaning |
|---|---|---|
| `sweep` · `area` · `diff` | hunters, writers, reviewers | the whole target, a sub-area, or the files of a diff |
| `design` | test-writer, test-reviewer | work the rows of a test design |
| `report` | test-designer, fix-verifier, docs-reconciler | from a bug report (regression anchors, cross-checks), or report-only for docs |
| `spec` | test-designer | acceptance tests from a spec or plan before code exists |
| `threat-model` · `review` | security-reviewer | build a threat model, or review a scope |
| `code` · `results` | benchmark-reviewer | review benchmark code, or judge measured results |
| `refute` | any reviewing role | the finding in `prior:` is a claim to break: answer **HOLDS** or **REFUTED** with the evidence (second votes, refutation passes) |

**Never** the author's intent or the orchestrator's opinion of the change: an independent reviewer that is told
"this is safe because X" becomes a rubber stamp.

## What an agent returns

The final message is the report and goes to the orchestrator, not the user: no preamble, no restating the diff.

- **Findings** (hunters, reviewers, verifiers): ranked 🔴 → 🟡 → 🔵, then 🟢 "done well" (specific, not
  flattery). Each finding: `file:line`, the category or rule (citing the rulebook section), the **concrete
  failure** (input, state or sequence → wrong outcome), and a fix. Formatted so the orchestrator can paste it as a
  bug-report finding (`reference/trackers/bug-reports-README.md`).
- **Verdicts** use exactly the vocabulary of the role: test review (`testing.md` §13), fix verification
  (CONFIRMED · INCOMPLETE · REGRESSION · NEW-BUG · UNVERIFIABLE · NO-TEST), benchmarks (Faster · Slower · Same ·
  Unstable · Contaminated), fixer classes (`testing.md` §14).
- **Not covered**: always last. What was skipped, what could not be run, what needs a human or a running system.
- Writers and fixers also list the files they changed and the gate result they observed.

## Severity

🔴 blocker: wrong, unsafe, or breaks something outside the change · 🟡 confirm: likely a problem, or right for a
reason the code does not show · 🔵 suggestion · 🟢 done well.

## Concurrency rules orchestrators enforce

- Read-only agents run in parallel (one message, several `Agent` calls).
- Builders run one at a time: two builds in one tree lock each other's outputs.
- A central gate runs **once, before** fan-out; reviewers then run tests without rebuilding.
- Never rebuild while a no-build reviewer is running.
- Each agent is told the rule that applies to it.

## The roster

### Agents (`plugins/stackfoundry/agents/`)

| Agent | Writes? | Tools | Job |
|---|---|---|---|
| `surveyor` | no | Read, Grep, Glob, Bash | Runs `stackfoundry survey`, confirms each hint against code, drafts the target map and the questions for the user |
| `stack-researcher` | its pack file only | Read, Grep, Glob, WebSearch, WebFetch, Write | Researches one technology into a pack (`reference/pack-research.md`) and writes it to the `output:` path its brief names |
| `bug-hunter` | no | Read, Grep, Glob, Bash | Hunts one category in one target's scope; findings with concrete failures |
| `fix-verifier` | no | Read, Grep, Glob, Bash | Adversarially verifies one landed fix; one verdict |
| `web-fix-verifier` | no | Read, Grep, Glob, Bash + browser tools | Same, with a live browser repro for UI targets |
| `test-designer` | no | Read, Grep, Glob, Bash | Risk-ranked test list for one area, each expected value with a cited oracle |
| `test-writer` | tests only | Read, Grep, Glob, Bash, Edit, Write | Writes tests on the existing harness to a design or an area; never production code |
| `test-reviewer` | no | Read, Grep, Glob, Bash | One verdict per test (`testing.md` §13), mutation-backed where a lane exists |
| `test-fixer` | tests + harness | Read, Grep, Glob, Bash, Edit | Classifies first (`testing.md` §14), fixes by cause, never loosens |
| `performance-reviewer` | no | Read, Grep, Glob, Bash, WebSearch, WebFetch | Two passes: the code, then current guidance from the web |
| `security-reviewer` | no | Read, Grep, Glob, Bash, WebSearch, WebFetch | Threat model from exposure and stakes, or a security review of a scope |
| `code-verifier` | no | Read, Grep, Glob, Bash | Stack plumbing: wiring, registration, routes, config keys, resources, CI job graphs resolve |
| `debugger` | no | Read, Grep, Glob, Bash | Reproduce → hypothesize → bisect → root cause with evidence; proposes the fix and the regression test |
| `change-reviewer` | no | Read, Grep, Glob, Bash | Reviews a diff as a stranger: correctness, concurrency, blast radius, contracts, security, convention fit |
| `code-semantics-reviewer` | no | Read, Grep, Glob, Bash | Duplication, hand-copies of generated truth, names that lie |
| `markup-semantics-reviewer` | no | Read, Grep, Glob, Bash | Templates and styles: semantic markup, misleading class names, re-declared styles |
| `docs-reconciler` | docs only | Read, Grep, Glob, Bash, Edit | One docs area against the code and `documentation.md`; mechanical fixes, flags judgment calls |
| `skill-agent-verifier` | `.claude/` only | Read, Grep, Glob, Bash, Edit | Skill/agent/rulebook plumbing in a repo or the plugin; mechanical fixes, flags the rest |
| `plan-sync-reviewer` | no | Read, Grep, Glob, Bash | Confirms a plan retirement landed: plan deleted, spec + index row, instructions synced |
| `test-runner` | no | Read, Grep, Glob, Bash (model: haiku) | Runs given test commands, returns only the summary |
| `benchmark-writer` | benchmarks only | Read, Grep, Glob, Bash, Edit, Write | Writes pre-registered benchmarks and dry-runs them |
| `benchmark-reviewer` | no | Read, Grep, Glob, Bash | Hunts benchmark defects (`benchmarking.md` §2) and judges results (§4) |

### Skills (`plugins/stackfoundry/skills/`)

`dmi` = `disable-model-invocation: true` (slash-only).

| Family | Skills |
|---|---|
| Core | `init` (dmi), `research-stack`, `sync`, `upgrade` (dmi), `materialize` (dmi), `configure-guards` (dmi), `write-code`, `skill-agent-author`, `skill-agent-verifier` |
| Tests | `design-tests`, `write-tests`, `review-tests`, `fix-tests`, `run-tests`, `scaffold-test-harness`, `setup-mutation` |
| Bugs and review | `bug-hunt`, `fix-verify`, `review-changes`, `quality-review`, `change-targets`, `quality-sweep`, `performance-review`, `security-review-target`, `threat-model` |
| Reactive | `debug`, `fix-ci` |
| Docs and backlog | `backlog`, `plan-feature`, `implement-plan`, `retire-plan`, `docs-reconciler` |
| Work modes | `with-plan`, `plan-execute`, `implement-only`, `elaborate-plan` (dmi), `ask-me`, `prune-comments` |
| Git | `github-prs` (dmi), `cleanup-merged` |
| Benchmarks | `write-benchmarks`, `run-benchmarks` |
| Dependencies and radar | `check-updates`, `act-on-updates` (dmi), `bump-all`, `bump`, `check-formats`, `tech-radar`, `act-on-radar` (dmi), `radar-digest`, `stackfoundry-radar`, `flaky-watch`, `schedule` (dmi) |

**A skill cannot `Skill`-invoke a dmi skill.** So dmi is only for entry points no other skill chains into; a skill
another skill calls (`bump-all`, `cleanup-merged`, `quality-sweep`, `sync`) stays model-invocable. Naming a dmi
skill to the user (`run /stackfoundry:init first`) is fine.

## Skill body shape

```markdown
---
name: <folder name>
description: <what + when, ≤ 250 chars>
argument-hint: "<args>"            # when it takes arguments
disable-model-invocation: true     # slash-only skills only
---

# <Title>

<one paragraph: what it does, what it never does, which rulebook governs it>

## Inputs / Modes
## Procedure        (numbered; facts read from the profile, never restated)
## Boundaries       (what it never writes or runs)
## Tooling          (the actual tools: Agent with subagent_type "stackfoundry:<agent>", Bash for
                     `stackfoundry <subcommand>`, AskUserQuestion, Skill → /stackfoundry:<skill>)
```

- Every skill and agent carries the **portable-form preamble** right under its title, exactly as
  `scripts/stackfoundry/preamble.py` writes it (`verify-plumbing` checks it). It defines `stackfoundry <subcommand>`
  as the launcher by path (`scripts/stackfoundry.sh`, or `stackfoundry.ps1` on Windows without `sh`), says what
  `${CLAUDE_PLUGIN_ROOT}` is where an assistant does not substitute it, and points at `reference/clients.md` for tool
  equivalents. So write the body in Claude Code's terms (`AskUserQuestion`, `subagent_type`, bare
  `stackfoundry …`), never per assistant. Dispatching skills give every agent `pluginRoot:` in the brief.
- Reference files are linked as `${CLAUDE_PLUGIN_ROOT}/reference/<path>`; Claude Code substitutes the variable, other
  assistants resolve it through the preamble.
- Settings are the repo's, in `.stackfoundry/config.json` (`clients`, `docsRoot`, `researchRefreshDays`,
  `defaultEffort`), read with `stackfoundry config <key>`, which fills in the defaults. No `${user_config.*}`: other
  assistants have no plugin settings.
- `<docsRoot>` in a skill body means `targets.json` → `docsRoot`; `{{docsRoot}}` is reserved for template
  placeholders.
- A code-writer skill is named after the **bare** app-model id: pack `app-model-nuxt-ssr` →
  `.claude/skills/nuxt-ssr-code-writer/`.
- Agents are dispatched with `subagent_type: "stackfoundry:<agent>"`; when a target has a materialized agent
  (`targets.json` → `materialized`), that repo agent is dispatched instead.
- Other skills are invoked with `Skill` → `stackfoundry:<skill>`, or named to the user as `/stackfoundry:<skill>`.
- An unattended skill (check-updates, tech-radar, stackfoundry-radar, flaky-watch, report-only docs-reconciler)
  asks nothing, installs nothing, writes exactly one report, never writes git, and ends with a `git status`
  comparison listing any side effect.

## Agent body shape

```markdown
---
name: <file name>
description: <job + when; "Read-only." when it writes nothing; ≤ 300 chars>
tools: <grant>
---

# <Title>

<one paragraph: the role, and why it is independent of the author>

## Read first        (the reading order above, plus the role's rulebook)
## What you look for / What you do   (method; the checklist comes from the pack rulebooks)
## What you must not do
## Verify before you report
## Report            (format and vocabulary)
## Tooling           (the tools it uses; verify-plumbing checks every backticked tool here against `tools:`)
```

`stackfoundry verify-plumbing` reads the `## Tooling` section of an agent as its instructions to use tools: a
backticked tool name there, on a line without a negation, must be in the grant. Name tools elsewhere freely.
