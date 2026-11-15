# What's next: 2026-11-13

Interactive run. No extensions applied (none exist for `whats-next` or `product-analyst`). Nothing has started yet;
any plans come from the items picked afterwards.

## Snapshot

**stackfoundry** is an open-source (MIT) plugin for AI coding assistants (Claude Code, Codex, GitHub Copilot,
Cursor, Gemini CLI, Antigravity CLI) for software teams and individual developers worldwide, at the MVP stage
(`.stackfoundry/product.json`). Release 0.5.0 is tagged at `ee69b5a`.

The domain brief `.stackfoundry/domain/ai-coding-assistant-plugin.json` (researched 2026-11-09, 4 days old, scope
unchanged) was reused. A fresh `product-analyst` audit of `cli` and `plugin` at 0.5.0 gives the verdicts below.

**Since the 2026-11-10 report:** items 1 (Antigravity channel), 3 (context budgets) and 4 (threat model, now
**Open: none**) landed, and item 5 (stale profile) partly. Three capabilities moved up: `instruction-size-budgets`
and `low-context-cost` to present, `host-migration-support` from missing to present. `security-policy` is now
rated partial, applying the brief's "supported versions" signal strictly. Item 2 became the plan
`docs/plans/host-smoke-matrix.md`.

## Recommended next steps

### 1. Say honestly which assistants are proven (product, S)

- **What:** mark Codex, Cursor, Gemini CLI and Antigravity CLI as experimental in `README.md` ("Other assistants"),
  linking the smoke table in `docs/release.md`. Bring the channel list into line everywhere: the README headline
  (line 3) and `product.json` `channels` omit Antigravity; `.stackfoundry/profile.md` "Users and channels" names
  Claude Code only. Fix "four smoke steps" in `docs/plans/host-smoke-matrix.md`, which lists five.
- **Why now:** `valid-manifest-per-client` and `marketplace-install` are **table-stakes** and still **partial**: a
  host skips a plugin whose manifest it cannot load [cc-plugins-ref, copilot-cli-plugins, codex-plugins]. Four of six
  rows in `docs/release.md` say "not run yet", yet the README lists all six without qualification. The brief's
  "conflicting instructions" weakness [cc-memory] shows here in the repo's own docs.
- **Impact:** users of an unproven assistant learn up front that it is unproven, instead of from a plugin that does
  not load or a guard that never fires.
- **Effort:** S. **Depends on:** nothing; the smoke plan (Already planned) later removes the labels it proves.
  **Confidence:** high.
- **First step:** a direct edit, or `/stackfoundry:docs-reconciler` on `README.md`, `.stackfoundry/` and
  `docs/plans/`.

### 2. Record the legal and support stance (product, S)

- **What:** add "Supported versions" to `SECURITY.md` (for example: the latest minor only). Add a short note
  recording the EU AI Act Art. 2(12) open-source exclusion assessment and its re-assessment trigger (an Art. 50 or
  high-risk change), and the Cyber Resilience Act position (non-commercial, no steward).
- **Why now:** `security-policy` is **partial** [gh-security-policy]; the AI Act assessment lives only in the
  brief's `questions` [eu-ai-act-art2]; the three CRA steward obligations are **unknown** [eu-cra-oss]. Unchanged
  since the 11-10 report, and the cheapest item on the list. Four minor releases in four days make "which version
  gets fixes" a real question.
- **Impact:** low today; it matters once anyone monetizes, redistributes or stewards the plugin.
- **Effort:** S. **Confidence:** medium (the brief read the AI Act and CRA on unofficial renderings).
- **First step:** a direct edit, or `/stackfoundry:plan-feature` "legal stance and supported versions".

### 3. Refresh the stale pack versions in this repo (technical, S)

- **What:** update `.stackfoundry/rules/app-model-claude-code-plugin.md`, `capability-claude-code-marketplace.md`,
  `tooling-claude-plugin-eval.md`, `tooling-github-actions.md`, their packs and their `.claude/rules/` copies. They
  say "Versions in use: 0.1.0" and CLI `2.1.307`; the truth is `plugin.json` 0.5.0 and `ci.yml` pin `2.1.319`.
- **Why now:** this is the brief's "stale generated guidance" weakness [cc-memory, cursor-rules], in the very
  rulebooks every agent working on `plugin` loads. The 11-10 fix covered the profiles, not the packs.
- **Impact:** agents reason about a CLI and plugin version two releases old; a rule written for 2.1.307 may already
  be wrong.
- **Effort:** S. **Depends on:** nothing. **Confidence:** high (verified in the files).
- **First step:** `/stackfoundry:docs-reconciler` on `.stackfoundry/rules/`; if a rule's content (not only its
  version line) needs updating, `/stackfoundry:research-stack` for that pack.

### 4. Detect conflicts between generated rules and a repo's own instructions (product, M)

- **What:** have `init`, `sync` and `docs-reconciler` report when a generated rulebook or profile contradicts the
  repo's existing `CLAUDE.md`, `AGENTS.md` or team rules, or another stackfoundry file.
- **Why now:** `instruction-audit` is **expected** and **partial** [cc-memory, copilot-instructions]. The checks
  since 0.2.0 are structural (`render-block --diff`, `size-check`, `change-targets` "Shadowed"); nothing compares
  meaning. `init` handles a name collision only. Items 1 and 3 are two conflicts in this repo that nothing caught.
  Unchanged since the 11-10 report, and no plan exists.
- **Impact:** an agent picks one of two contradicting rules arbitrarily; the result is hard to debug.
- **Effort:** M. **Confidence:** medium.
- **First step:** `/stackfoundry:plan-feature` "instruction conflict check".

### 5. Run the evals for real, add negative cases, publish the uplift (product and technical, M)

- **What:** get one recorded eval run at 0.5.0 (the only result, 0.1.0, ended `auth_failed`); add
  should-not-trigger cases; record the with- versus without-plugin delta in `docs/`; then decide whether the
  `evals.yml` lane runs on a schedule with a threshold above 0.
- **Why now:** `behavioral-evals` is **expected** and **partial**: 9 cases for 56 skills and 25 agents, and
  `.github/workflows/evals.yml` runs only on manual dispatch with `--threshold 0`. `measured-uplift` is a
  **differentiator**, partial: the arms exist, no delta is recorded [cc-plugin-evals]. A 2026 evaluation found that
  repository context files did not generally raise task success and raised cost by over 20% [agents-md-eval]; that
  is the product's core claim to prove. Copilot's default model ignored the bare walkthrough request
  (`docs/release.md`), the "skills that never trigger" weakness.
- **Impact:** without a published delta, the main claim rests on assertion.
- **Effort:** M; each run costs tokens. **Confidence:** high on the gap.
- **First step:** `/stackfoundry:plan-feature` "eval run, negative cases and published deltas".

### 6. Committed team install for the other assistants (product, M)

- **What:** have `init` write each enabled client's project-level install settings, the way it writes
  `.claude/settings.json` for Claude Code, where the host supports it.
- **Why now:** `team-scope-install` is **expected** and **partial**: Claude Code only [cc-plugin-install,
  copilot-cli-plugins].
- **Impact:** each Copilot, Codex or Cursor collaborator installs by hand, or never does.
- **Effort:** M. **Depends on:** the smoke plan, so the format is proven per host first. **Confidence:** medium.
- **First step:** `/stackfoundry:plan-feature` "team install per assistant".

### 7. Nested instruction files for monorepos (product, M)

- **What:** let `render-block` write a per-package `AGENTS.md` (and `GEMINI.md`) for hosts without path-scoped
  rules, so Codex and Gemini get target guidance where they read it.
- **Why now:** `nested-monorepo-instructions` is **expected** and **partial** [agents-md, codex-agents-md]:
  `block.py` `instruction_files` writes only root files. Codex's 32 KiB budget is measured on the root file only.
- **Impact:** in a monorepo, Codex and Gemini see no per-target guidance.
- **Effort:** M. **Confidence:** medium.
- **First step:** `/stackfoundry:plan-feature` "nested instruction files".

## Capability map

| Capability | Tier | Status | Evidence | Source |
|---|---|---|---|---|
| valid-manifest-per-client | table-stakes | partial (planned) | host validator only for Claude Code (`ci.yml` `validate`); own key checks for others | cc-plugins-ref, copilot-cli-plugins, codex-plugins |
| marketplace-install | table-stakes | partial (planned) | `docs/release.md`: proven Claude Code, Copilot; not run Codex, Cursor, Gemini, Antigravity | cc-plugin-install, copilot-cli-plugins, codex-plugins, gemini-extensions |
| skills-spec-conformance | table-stakes | present | `plumbing.py` `PORTABLE_NAME`, caps, trigger clause | skills-spec, skills-best-practices |
| native-instruction-formats | table-stakes | present | `clients.py` `RULE_FORMATS` (now with Antigravity) | agents-md, cc-memory, copilot-instructions, cursor-rules, codex-agents-md |
| instruction-size-budgets | table-stakes | **present** ↑ | `sizes.py`, `clients.py` `LIMITS`, `block.py` `BLOCK_BUDGET`; Antigravity's combined budget not measured | cc-memory, cursor-rules, skills-spec, codex-agents-md |
| untrusted-input-boundary | table-stakes | present | data clauses; `plumbing.py` rejects shell plus web; `web-researcher` agent; injection eval | owasp-llm01, snyk-skills |
| self-contained-package | table-stakes | present | no network code; `SECURITY.md` design commitments | snyk-skills |
| update-safe-paths | table-stakes | present | quoted `${CLAUDE_PLUGIN_ROOT}` in `hooks/hooks.json` | cc-plugins-ref, skills-best-practices |
| path-scoped-rules | expected | present | `render_rule`, `globs-check` | cc-memory, copilot-instructions, cursor-rules |
| nested-monorepo-instructions | expected | partial | root files only (`block.py` `instruction_files`) | agents-md, codex-agents-md, cursor-rules |
| reference-not-copy | expected | present | `Here:` anchors, `volatile-facts` | cursor-rules, skills-best-practices |
| instruction-audit | expected | partial | structural checks only; no conflict detection | cc-memory, copilot-instructions |
| enforced-guards | expected | present | `guard.py` adapters for six hosts | cc-memory, copilot-cli-plugins, codex-plugins |
| deterministic-helper-scripts | expected | present | `cli.py`, new `size-check`, `render-block`, `render-target`, `schedule` | skills-best-practices |
| team-scope-install | expected | partial | Claude Code `settings.json` only | cc-plugin-install, copilot-cli-plugins |
| versioned-releases | expected | present | tags v0.2.0–v0.5.0, CHANGELOG, `release.yml` | cc-plugins-ref, cc-plugin-install |
| low-context-cost | expected | **present** ↑ | `plumbing.py` `LISTING_CAP` 22,000; listing ≈19.2k characters | cc-plugin-install, skills-spec |
| behavioral-evals | expected | partial | 9 cases; manual-only `evals.yml`, threshold 0; no negative cases | cc-plugin-evals, skills-best-practices |
| security-policy | expected | **partial** ↓ | `SECURITY.md` has no supported versions | gh-security-policy |
| single-source-multi-client | differentiator | present | `build_clients.py --check` in CI and release | agent-plugins, copilot-cli-plugins |
| minimal-nonobvious-instructions | differentiator | present | `pack-research.md`; short pointer block since 0.4.0 | agents-md-eval, cursor-rules |
| cited-current-research | differentiator | present | `cited.py`, pack and domain schemas | so-survey-2025-ai, skills-best-practices |
| measured-uplift | differentiator | partial | with/without arms; no recorded delta | cc-plugin-evals, agents-md-eval |
| host-migration-support | differentiator | **present** ↑ | `build_antigravity`, `release.yml`, radar watches every assistant; never smoke-tested | google-antigravity, gemini-extensions |

| Regulation | Obligation | Status | Evidence |
|---|---|---|---|
| EU CRA, open-source provisions | record whether monetized | met | `product.json` `monetization`, `LICENSE` |
| EU CRA | steward: cybersecurity policy, cooperation, reporting | unknown | no steward recorded; `SECURITY.md` covers intake only |
| EU AI Act Art. 2(12) | record the open-source exclusion assessment | partial | only in the brief's `questions` |
| EU AI Act Art. 2(12) | re-assess on an Art. 50 or high-risk change | unknown | no trigger recorded |

## Weaknesses now

- **Unproven channels:** four of six assistants never run; open *confirm* items in
  `plugins/stackfoundry/reference/clients.md` (item 1; plan `host-smoke-matrix.md`).
- **Conflicting facts in this repo:** channel lists disagree across README, `product.json` and `profile.md` (item 1).
- **Stale pack versions** in four rulebooks (item 3).
- **Role rules enforced in Claude Code only:** other hosts send no `agent_type` (`reference/clients.md` "Which agent
  made the call"), so read-only roles are advice there.
- **Windows without Git Bash:** the Claude Code and Antigravity hooks do not run and the guard fails open silently
  apart from `guard --check` (documented, threat-model T18). This machine is Windows.
- **No technical reports yet:** `docs/radar/`, `docs/dependency-reports/`, `docs/performance-reports/`,
  `docs/bug-reports/` and `docs/test-designs/` hold only READMEs, so the technical track rests on the audit.
- No open threat-model gaps (`docs/security/plugin-threat-model.md`, **Open: none**); no open bugs or TODOs (the one
  backlog TODO is test data in `tests/test_docs_tools.py:77`).

## Strengths

- A threat model with every gap closed and a test or eval per fix (`docs/security/plugin-threat-model.md`).
- One guard serves six hosts' hook formats and fails open by design (`guard.py`, `tests/test_guard_clients.py`).
- Context budgets per host in one cited table (`clients.py` `LIMITS`), enforced by `size-check` and the listing cap.
- Generated client files are held equal to the source in CI, the pre-commit hook and the release workflow
  (`scripts/build_clients.py --check`).
- Unattended runs now carry minimal, owned permission rules and report every denied call (`schedule rules|check`,
  0.5.0).
- Every researched rule and domain claim cites its source (`cited.py`).

## Direction

- **Portable plugin packaging** and **host consolidation** (emerging) [agent-plugins, google-antigravity]: the
  outputs exist; proving them (Already planned) is now the gap, not building them.
- **Context-cost transparency** and **minimal context files** (emerging) [cc-plugin-install, agents-md-eval]:
  budgets landed; the measured uplift (item 5) is what remains.
- **Skill supply-chain security** (growing) [snyk-skills]: covered by the closed threat model; keep it current.
- There is still no tech-radar report. `/stackfoundry:tech-radar` would add the stack's own direction and would
  also flag stale packs like item 3.

## Already planned

- `docs/plans/host-smoke-matrix.md` (Prove every advertised assistant). **Should move up:** it closes the only two
  table-stakes gaps. Copilot CLI 1.0.15 is installed on this machine, so its row (agents, guard, extension) can be
  finished now. Codex, Cursor, Gemini and `agy` are not installed. The plan's README-labelling step overlaps item 1;
  doing item 1 now does not block it.
- `docs/plans/deferred-upgrades.md`: empty ledger.
- Follow-ups in `docs/specifications/antigravity-channel.md:76-78` (real `agy` smoke test) fold into the smoke plan.

## Not reached

- **Brief sources** never read (brief `notReached`): the Agent Plugins 1.0 spec text, the official AI Act and CRA
  texts, Cursor's plugin docs, the full DORA 2025 report.
- **The audit:** no host was installed or run; no gates or evals were run; not every SKILL.md and agent body was
  read.
- `needsResearch`: none.

## Assumptions

- The 2026-11-09 brief was reused without asking: it is 4 days old and the product's scope has not moved.
- Churn over 6 months concentrates in `plugins/stackfoundry/skills` (372 file touches), `scripts` (179), `agents` and
  `reference`; `tests` (99) keeps pace, so there is no untested hot area.
- Item 2 ranks above the technical items because the method ranks regulation obligations first, though its impact
  is low today. Items 1–3 are all S and can land together.
