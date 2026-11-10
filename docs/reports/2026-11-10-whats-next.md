# What's next: 2026-11-10

Interactive run. Nothing has started yet; any plans come from the items picked afterwards.

## Snapshot

**stackfoundry** is an open-source (MIT) plugin for AI coding assistants: Claude Code, Codex, GitHub Copilot,
Cursor and Gemini CLI. Its audience is software teams and individual developers worldwide, and it is at the MVP
stage (`.stackfoundry/product.json`). Release 0.2.0 is tagged at `efeb079`.

The domain brief `.stackfoundry/domain/ai-coding-assistant-plugin.json` was researched on 2026-11-09 (one day old,
refreshed every 90 days) for the same product profile. It has 24 capabilities (8 table-stakes), 2 regulations,
12 weaknesses, 9 trends and 23 sources. The capability verdicts below come from a fresh `product-analyst` audit of
the `cli` and `plugin` targets at 0.2.0.

## Recommended next steps

### 1. Follow Gemini CLI to Antigravity CLI, or retire the channel (product, M)

- **What:** add an Antigravity plugin output, or drop Gemini CLI from the supported assistants, then update the
  README install row, `.github/workflows/release.yml`, `plugins/stackfoundry/reference/clients.md` and
  `product.json` `channels`.
- **Why now:**
  - Google stopped serving Gemini CLI to individual tiers on 2026-06-18 and moved those users to Antigravity CLI,
    where extensions became plugins [google-antigravity]. The brief lists "host churn strands users" as a domain
    weakness.
  - The repo still ships the old path: `README.md` installs with `gemini extensions install`, and
    `scripts/build_clients.py` `build_gemini()` builds the release asset that 0.2.0 just attached.
  - Capability `host-migration-support` is **missing**, and `skills/stackfoundry-radar` watches only Claude Code
    releases.
- **Impact:** individual users who follow the README end up on a retired client, and the README advertises a
  channel the project has never proven (see item 2).
- **Effort:** M. **Depends on:** nothing.
- **Confidence:** medium. The brief could not read Antigravity's plugin reference (`notReached`), so its format
  needs research first.
- **First step:** `/stackfoundry:plan-feature` "Antigravity CLI channel (or retire Gemini)".

### 2. Prove the other assistants' installs and hooks (technical, M)

- **What:** run the smoke matrix in `docs/release.md` in Codex, Cursor and Gemini or Antigravity: install,
  listing, guard denial and a plain request. Also finish Copilot (agents, guard). Mark any channel that cannot be
  proven as experimental in the README.
- **Why now:** two table-stakes capabilities are only **partial**:
  - `valid-manifest-per-client`: only Claude Code's manifests pass a host validator;
  - `marketplace-install`: only Claude Code and Copilot are proven.
  `docs/release.md` still shows "not run yet" for Codex, Cursor and Gemini CLI. The brief says a host skips a
  plugin whose manifest it cannot load [cc-plugins-ref, copilot-cli-plugins, codex-plugins]. 0.2.0 now ships to
  all five.
- **Impact:** users of an unproven assistant may get a plugin that does not load, or whose guard never fires.
- **Effort:** M. It needs each host's CLI installed, and the guard has open *confirm* items in `clients.md`.
- **Depends on:** item 1 for the Gemini row.
- **Confidence:** high on the gap; the breakage itself is unproven.
- **First step:** install the Codex and Cursor CLIs, then run the smoke steps from `docs/release.md`.

### 3. Budget the size of generated context per assistant (product, M)

- **What:**
  - Check generated rulebooks, instruction blocks, code-writer skills and SKILL.md bodies against each host's
    limits (lines, bytes) in `stackfoundry` (for example `globs-check`, `verify-plumbing` or `pack check`).
  - Track the plugin's always-on listing cost: about 13k characters of skill descriptions and 7k of agent
    descriptions, loaded every session.
- **Why now:**
  - `instruction-size-budgets` is **table-stakes** and **partial** [cc-memory, cursor-rules, codex-agents-md,
    skills-spec]. Hosts now show a plugin's token cost before install [cc-plugin-install].
  - Today only description lengths are capped (`plugins/stackfoundry/scripts/stackfoundry/plumbing.py`
    `SKILL_CAP`, `AGENT_CAP`), and `reference/pack-research.md` "Output size" is advice, not a check.
- **Impact:** a large repo can get rulebooks a host cuts off silently, and every session pays the listing cost.
- **Effort:** M. **Depends on:** nothing. **Confidence:** high.
- **First step:** `/stackfoundry:plan-feature` "context budgets per assistant".

### 4. Threat-model the agents that hold a shell and the web (technical, S to start)

- **What:** write the first threat model for `plugin`, whose stakes are safety and data integrity. Decide whether
  `security-reviewer` and `performance-reviewer` need `Bash` alongside `WebSearch`/`WebFetch`, and whether the guard
  should ask before networked shell commands.
- **Why now:**
  - `untrusted-input-boundary` is table-stakes [owasp-llm01, snyk-skills]. It is present (every agent has a
    "content is data" clause), but `agents/security-reviewer.md` and `agents/performance-reviewer.md` combine a
    shell with fetched pages.
  - Read-only reviewers also hold `Bash`, so "read-only" is advice, not enforcement (weakness "rules that must hold
    written only as advice" [cc-memory]).
  - `docs/security/` has no threat model.
- **Impact:** a hostile page or repo file could steer a reviewer into running commands on a user's machine.
- **Effort:** S for the model; the follow-ups depend on it. **Confidence:** medium (the exposure is real, but no
  exploit has been shown).
- **First step:** `/stackfoundry:threat-model plugin`.

### 5. Fix the stale facts in this repo's own profile (technical, S)

- **What:** correct the files that drifted:
  - `.stackfoundry/product.json` evidence still says "not yet released", though 0.2.0 is tagged;
  - `.stackfoundry/targets/cli.md` lists `plugins/stackfoundry/bin/**`, which no longer exists;
  - `.stackfoundry/targets/cli.md`, `targets/plugin.md` and `profile.md` say "Generated: none", while
    `targets.json` `generated` and `guards.json` list the generated client files.
- **Why now:** these are domain weaknesses found in this repo: "stale generated guidance" and "conflicting
  instructions" [cc-memory, cursor-rules]. Every role agent reads these files first.
- **Impact:** agents working on stackfoundry get contradicting facts about what is generated.
- **Effort:** S. **Depends on:** nothing. **Confidence:** high (the analyst confirmed each in the files).
- **First step:** `/stackfoundry:docs-reconciler` on `.stackfoundry/`, or a direct edit.

### 6. Detect conflicts between generated rules and the repo's own instructions (product, M)

- **What:** have `init`, `sync` and `docs-reconciler` report when a generated rulebook or profile contradicts the
  repo's existing CLAUDE.md, AGENTS.md or rules, or another stackfoundry file.
- **Why now:** `instruction-audit` is **expected** and **partial** [cc-memory, copilot-instructions]. Today's checks
  are structural (`agents/skill-agent-verifier.md`, `plumbing.py`), and item 5 shows the gap in this very repo.
- **Impact:** agents pick one of two contradicting rules arbitrarily, and the result is hard to debug.
- **Effort:** M. **Depends on:** nothing. **Confidence:** medium.
- **First step:** `/stackfoundry:plan-feature` "instruction conflict check".

### 7. Run the evals in CI and publish the uplift (product and technical, M)

- **What:**
  - Get the existing eval cases running (the only local run, on 0.1.0, ended in `auth_failed`).
  - Record the with-plugin vs. without-plugin deltas in `docs/`.
  - Add a CI lane for the cheap cases and add should-not-trigger cases.
- **Why now:**
  - `behavioral-evals` is **expected** and **partial**: 8 cases for 56 skills and 24 agents, none in
    `.github/workflows/ci.yml`.
  - `measured-uplift` is a **differentiator**, also partial [cc-plugin-evals].
  - A 2026 evaluation found that repository context files did not generally raise task success and raised
    inference cost by more than 20% [agents-md-eval]. That is the product's core claim to prove.
  - Developer trust in AI output is low: 33% trust it, 46% distrust it [so-survey-2025-ai].
- **Impact:** without a published delta, the main claim rests on assertion.
- **Effort:** M. Each run costs tokens, so the CI lane should run cheap cases only.
- **Depends on:** item 3 helps judge which sections earn their cost.
- **Confidence:** high on the gap.
- **First step:** `/stackfoundry:plan-feature` "eval lane and published deltas".

### 8. Record the legal and support stance (product, S)

- **What:** add a "Supported versions" section to `SECURITY.md`, plus a short note recording two assessments: the
  EU AI Act's open-source exclusion (Art. 2(12)) and the Cyber Resilience Act's non-commercial position.
- **Why now:**
  - Regulation obligations are **partial**: the AI Act assessment exists only as an open question in the brief
    [eu-ai-act-art2], and the CRA steward obligations are **unknown** [eu-cra-oss].
  - `security-policy` is present but has no supported versions [gh-security-policy].
- **Impact:** low today. It matters as soon as anyone monetizes the plugin or acts as its steward.
- **Effort:** S. **Confidence:** medium. The brief read the AI Act on an unofficial rendering (`notReached`).
- **First step:** `/stackfoundry:plan-feature` "legal stance and supported versions", or a direct edit.

## Capability map

| Capability | Tier | Status | Evidence | Source |
|---|---|---|---|---|
| valid-manifest-per-client | table-stakes | partial | CI validates only Claude Code's; `docs/release.md` smoke table | cc-plugins-ref, copilot-cli-plugins, codex-plugins |
| marketplace-install | table-stakes | partial | proven: Claude Code, Copilot; not run: Codex, Cursor, Gemini | cc-plugin-install, copilot-cli-plugins, codex-plugins, gemini-extensions |
| skills-spec-conformance | table-stakes | present | `plumbing.py` name, cap and trigger checks | skills-spec, skills-best-practices |
| native-instruction-formats | table-stakes | present | `clients.py` `RULE_FORMATS`, `render_rule` | agents-md, cc-memory, copilot-instructions, cursor-rules, codex-agents-md |
| instruction-size-budgets | table-stakes | partial | only description caps in `plumbing.py` | cc-memory, cursor-rules, skills-spec, codex-agents-md |
| untrusted-input-boundary | table-stakes | present | data clauses in every agent; Bash plus web in two agents | owasp-llm01, snyk-skills |
| self-contained-package | table-stakes | present | no network code in `scripts/stackfoundry/`; `SECURITY.md` | snyk-skills |
| update-safe-paths | table-stakes | present | quoted plugin root; state lives in the repo | cc-plugins-ref, skills-best-practices |
| path-scoped-rules | expected | present | `render_rule`, `globs-check` | cc-memory, copilot-instructions, cursor-rules |
| nested-monorepo-instructions | expected | partial | root `AGENTS.md` only; no nested files | agents-md, codex-agents-md, cursor-rules |
| reference-not-copy | expected | present | `Here:` paths in rulebooks, `volatile-facts` | cursor-rules, skills-best-practices |
| instruction-audit | expected | partial | structural checks only | cc-memory, copilot-instructions |
| enforced-guards | expected | present | `guard.py` with per-client adapters | cc-memory, copilot-cli-plugins, codex-plugins |
| deterministic-helper-scripts | expected | present | `cli.py` subcommands | skills-best-practices |
| team-scope-install | expected | partial | Claude Code `settings.json` only | cc-plugin-install, copilot-cli-plugins |
| versioned-releases | expected | present | 0.2.0 tag, CHANGELOG, `docs/release.md` | cc-plugins-ref, cc-plugin-install |
| low-context-cost | expected | partial | per-description caps, no total budget | cc-plugin-install, skills-spec |
| behavioral-evals | expected | partial | 8 cases; no CI lane | cc-plugin-evals, skills-best-practices |
| security-policy | expected | present | `SECURITY.md` (no supported versions) | gh-security-policy |
| single-source-multi-client | differentiator | present | `scripts/build_clients.py` with `--check` in CI | agent-plugins, copilot-cli-plugins |
| minimal-nonobvious-instructions | differentiator | present | `reference/pack-research.md` "decisions, not tutorials" | agents-md-eval, cursor-rules |
| cited-current-research | differentiator | present | pack and domain schemas, `cited.py` | so-survey-2025-ai, skills-best-practices |
| measured-uplift | differentiator | partial | two eval arms exist; no recorded delta | cc-plugin-evals, agents-md-eval |
| host-migration-support | differentiator | missing | Gemini CLI paths only; no Antigravity output | google-antigravity, gemini-extensions |

| Regulation | Obligation | Status | Evidence |
|---|---|---|---|
| EU Cyber Resilience Act, open-source provisions | record whether the product is monetized | met | `product.json` `monetization`, `LICENSE` |
| EU Cyber Resilience Act | steward duties (security policy, cooperation, reporting) | unknown | no steward recorded; `SECURITY.md` covers intake only |
| EU AI Act Art. 2(12) | record the open-source exclusion assessment | partial | only in the brief's `questions` |

## Weaknesses now

- **Host churn:** Gemini CLI is packaged for, but individual users have moved to Antigravity (item 1).
- **Unproven channels:** Codex, Cursor and Gemini installs and guards have not been run (item 2).
- **No size budget** for generated context; silent truncation is possible (item 3).
- **Shell plus web in two reviewer agents;** read-only is advice for agents that hold `Bash` (item 4).
- **Stale and conflicting facts** in this repo's own profile (item 5).
- **Skills that may not trigger outside Claude Code:** Copilot's default model ignored the bare walkthrough request
  (`docs/release.md`). There are trigger graders for only three skills and no negative cases (item 7).
- No open bug reports, threat models, or radar or dependency reports exist yet (`docs/`), so the technical picture
  comes from the audit alone.

## Strengths

- One guard command serves five hosts' hook formats and fails open (`scripts/stackfoundry/guard.py`,
  `tests/test_guard_clients.py`).
- The generated per-assistant files are kept equal to the source in CI and in the pre-commit hook
  (`scripts/build_clients.py --check`).
- Repo extensions survive upgrades through a three-way merge (`scripts/stackfoundry/extensions.py`,
  `reference/extensions.md`).
- The manifest lock lets `upgrade` tell untouched files from team edits (`scripts/stackfoundry/manifest.py`).
- Every researched rule and domain claim cites its source (`cited.py`, the pack and domain schemas).
- Fixture repos with planted defects drive both the unit tests and the evals (`fixtures/`).

## Direction

These trends from the brief fit the stage and goals:

- **Agent Skills and AGENTS.md as shared formats** (mainstream) [skills-spec, agents-md]: already the core of the
  design.
- **Portable plugin packaging** (emerging) [agent-plugins]: the Agent Plugins 1.0 output exists, but the brief could
  not read the spec text. Re-check it when items 1 and 2 run.
- **Context-cost transparency** and **minimal, requirement-only context files** (emerging) [cc-plugin-install,
  agents-md-eval]: these drive items 3 and 7.
- **Skill supply-chain security** (growing) [snyk-skills]: this drives item 4.
- **Host consolidation and renames** (emerging) [google-antigravity]: item 1 now, and a reason for
  `stackfoundry-radar` to watch every channel, not only Claude Code.

There is no tech-radar report for this repo yet. `/stackfoundry:tech-radar` would add the stack's own direction.

## Already planned

- `docs/plans/deferred-upgrades.md`: deferred dependency upgrades only. No feature plan overlaps the items above.

## Not reached

- **Brief sources** that were not read (from the brief's `notReached`):
  - the Antigravity plugin reference and migration guide;
  - the Agent Plugins 1.0 spec text;
  - Cursor's plugin docs;
  - the official AI Act and CRA texts;
  - the full DORA 2025 report.
- **The audit:** nothing was run (gates, evals). Not every SKILL.md and agent body was read; trust wording was
  checked by search. The host claims in `reference/clients.md` were not verified against the hosts.

## Assumptions

- The brief from the 2026-11-09 run was reused at the user's choice, since the product profile is unchanged.
- Churn over the last 6 months concentrates in `plugins/stackfoundry/skills` and `scripts`, as expected for a
  young MVP. It was not used for ranking beyond confirming where the work is.
- Items 1 and 2 rank first because they affect users of the just-released 0.2.0 on channels the README advertises.
