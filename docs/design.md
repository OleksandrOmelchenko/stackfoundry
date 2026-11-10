# stackfoundry design

## Where it comes from

stackfoundry is extracted from a private production repository (a .NET + Vue/Nuxt + Angular + SQL Server shop) whose
`.claude/` grew to dozens of skills, around a hundred agents and a set of path-scoped rulebooks. Under the volume it
follows five patterns, and those patterns are what this plugin generalizes. The files themselves are not reused: they
named one codebase.

| Pattern | What it means here |
|---|---|
| **Rulebooks hold the truth; skills index them** | Facts live in one path-scoped rulebook. A skill links to it and never restates it, because a copy drifts silently |
| **Role × target** | One orchestrator skill per role; the role runs once per target. About four fifths of a per-target agent is the role and one fifth is target facts, so the role ships in the plugin and the facts in the repo |
| **Convergent pairs** | Every generator has an adversarial checker (bug-hunt ↔ fix-verify, write-tests ↔ review-tests ↔ fix-tests, benchmark writer ↔ reviewer), and a finding is verified before it is reported |
| **Living trackers with stable ids** | Reports are files with ids and markers (⬜ open, ✅ fixed, ⚠️ partial, 🚫 won't fix); the skill that fixes something flips its marker in the same change |
| **Discover vs apply** | Read-only discovery that can run unattended writes a report; an interactive skill reads it, asks once, and routes each item to the skill that owns it |

## Layers: a stack is not a language

A target's stack is a list of **packs**, each in one layer:

| Layer | Owns |
|---|---|
| **language** | syntax and style, analyzers and linters, formatter, typing and nullability, package-ecosystem mechanics, the SDK/runtime pin |
| **app-model** | lifecycle, threading and async model, hosting and DI, request or UI model, typical bug classes, performance profile, end-to-end testing, how it ships |
| **capability** | a concern that crosses app models: an ORM, an auth server, OpenAPI client generation, i18n, an outbox, a search engine, a regulated domain |
| **tooling** | test frameworks and runners, mutation tools, CI, containers, infrastructure-as-code |

C# in ASP.NET Core and C# in WPF share the `csharp` language pack and differ in app model; TypeScript in a Vue SPA and
in a Nuxt server share `typescript` and differ in app model, even inside the same folder. Consequences:

- each pack generates its own path-scoped rulebook; language rulebooks match by extension, app-model and capability
  rulebooks match the folders of the targets that use them;
- detection is per layer, from strong signals (an SDK attribute, a framework config file, a package reference), and
  ambiguity is asked, never guessed;
- a role reads every layer of its target, so the desktop target's bug hunter gets UI-thread and binding categories
  and never the API's request-scope and IDOR categories;
- package bumps key on the ecosystem (one per package manager); gates key on the target (each target that the
  ecosystem reaches is built and tested);
- the code-writer skill is per app model, not per language.

The reference is `plugins/stackfoundry/reference/layers.md`.

## No shipped technology content

The plugin ships the **method**: the layer taxonomy, the schemas, the research procedure, the role agents and the
rulebook and tracker templates. It ships no rules about any particular technology. `init` researches each detected
technology from current official sources (release notes, migration guides, security advisories, framework docs) and
writes the pack into the repo with every claim citing a URL, a version and an access date. `tech-radar` flags packs
older than the refresh window or behind the version the repo now uses, and `act-on-radar` routes them to
`research-stack`.

Why: a shipped rule about a framework is stale the day the framework ships its next major, and it reads as
authoritative. A researched rule carries its source and date, so its age is visible and refreshable.

## Procedure in the plugin, facts in the repo

| Plugin | Repo (written by `init`) |
|---|---|
| orchestrator skills | `.stackfoundry/profile.md`: the product, users, risk surfaces, compliance regime, git policy |
| generic role agents | `.stackfoundry/targets.json`: targets, paths, packs, gates, harness, test dirs, exposure, path rules, specialists |
| reference (method) | `.stackfoundry/targets/<target>.md`: stack facts, categories, oracle sources, traps |
| helper CLI and hooks | `.stackfoundry/ecosystems.json`, `guards.json`, `packs/<layer>-<tech>/` |
| | `.stackfoundry/rules/<layer>-<tech>.md` and each assistant's copy, `<app-model>-code-writer` skills |
| | tracker scaffolds under the docs root; `manifest.lock.json` |

Two reasons. Plugins cannot ship path-scoped rules or CLAUDE.md content, so the rules have to be in the repo anyway.
And procedure has to be upgradable: a skill copied into every repo at install time freezes there.

## The loops

The skills form loops, each a generator with its checker or a discover step with its apply step:

- **Tests**: `design-tests` → `write-tests` → `review-tests` → `fix-tests`. Expected values cite a source, never the
  code's output; a new test passes three shuffled runs and adds coverage or kills a mutant.
- **Bugs**: `bug-hunt` (read-only, per-category fan-out, adversarial verification) ↔ `fix-verify` (one verdict per
  landed fix). Findings live in trackers with stable ids.
- **Reactive**: `debug` (reproduce → bisect → fix → regression test) and `fix-ci`.
- **Security**: `threat-model` per target from its exposure, then `security-review-target`.
- **Review**: `review-changes` dispatches independent reviewers that are never told the author's intent.
- **Dependencies**: `check-updates` (unattended, report-only) → `act-on-updates` (asks once, routes) → `bump-all`.
- **Radar**: `tech-radar` (unattended) researches new versions, tools, practices and advisories per technology →
  `act-on-radar` routes each item (adopt, bump, migrate, trial, watch, reject).
- **Docs and backlog**: `plan-feature`, `implement-plan`, `retire-plan`, `backlog`, `docs-reconciler`.

`schedule` registers the unattended ones as scheduled tasks.

## One source, every assistant

The plugin is written once, in Claude Code's terms, and runs in Codex, GitHub Copilot, Cursor and Gemini CLI too
(`plugins/stackfoundry/reference/clients.md` maps them). Three things make that work without per-assistant copies
kept by hand:

- **The shared standards carry the core.** Skills are Agent Skills (`SKILL.md`), which every one of them reads.
  Codex, Copilot and Cursor also read an Agent Plugins 1.0 `plugin.json`, which `scripts/build_clients.py`
  generates beside Claude Code's manifest, together with the parts no standard covers: Copilot's agent files, each
  assistant's hook file, the Cursor manifest, the three extra marketplaces and, on release, a Gemini CLI extension.
  `--check` in CI and the pre-commit hook keeps them equal to the source.
- **Every skill and agent says how to read it elsewhere.** A preamble under each title gives the CLI by path,
  the plugin root where `${CLAUDE_PLUGIN_ROOT}` is not substituted, and the pointer to the tool equivalents.
- **The repo's files are written once and copied by the CLI.** Rulebooks are canonical in `.stackfoundry/rules/`:
  a pack's is rendered from its `pack.json` (`stackfoundry pack render`), a shared one (testing, dependency bumps,
  documentation, benchmarking) is filled from the profile (`stackfoundry render-rulebook`), and either is then
  rendered into each assistant's path-scoped format (`stackfoundry render-rule`); assistants without one read
  the canonical file through the table in their instruction file. Team agents are canonical in
  `.stackfoundry/agents/` and rendered the same way (`render-agent`). `stackfoundry outputs` is the one place that
  decides which assistant gets which copy, from `.stackfoundry/config.json`'s `clients`.

The guard is one command for every assistant's pre-tool hook; it tells the assistant from the event's shape and
answers in its format (see *Guards*).

### Role agents

One agent per role (`bug-hunter`, `fix-verifier`, `test-designer`, `test-writer`, `test-reviewer`, `test-fixer`,
`performance-reviewer`, `security-reviewer`, `code-verifier`, …). The orchestrator passes `target`, and the agent
reads that target's profile and rulebooks. Variants exist only where tool grants must differ (`web-fix-verifier` has
the browser tools). Claude Code loads every agent description in each session and warns past a budget, so one agent
per role, instead of one per role × target, is also what keeps the listing small.

`/stackfoundry:materialize <target> <role>` writes a dedicated agent into the repo when a team wants to hand-tune one
(a security-weighted auth server, say). The manifest records it, and `upgrade` leaves it alone.

### Every skill starts from plain language

A user says "set up stackfoundry in this repo" or "find bugs in the API", not a skill name, and only Claude Code has
a slash form for plugin skills. So no plugin skill sets `disable-model-invocation: true`, and every description ends
in a `Use for "…"` (or `Use when`/`to`/`after`/`before`) clause in the words a user would type. `verify-plumbing`
enforces both. Entry points a person starts on purpose (`init`, `upgrade`, `materialize`, `elaborate-plan`, the
`act-on-*` skills, `github-prs`, `schedule`) say "Only when asked." so they are not picked mid-task, and each
confirms before it writes. The cost is that their descriptions now count against the skill listing's share of the
context window. `walkthrough` is the entry for a user who doesn't know what to ask; its group table names
every skill, and `verify-plumbing` checks that none is left out.

## The helper CLI

`plugins/stackfoundry/scripts/stackfoundry.sh` is a POSIX `sh` launcher that finds Python 3.11+ (`python3`, `python`,
`py -3`) and runs `scripts/stackfoundry/cli.py` isolated (`-I`); `stackfoundry.ps1` does the same on Windows without
`sh`. Skills call it by path through their preamble, not from a `bin/` on `PATH`, which only Claude Code provides and
which keeps a plugin off claude.ai and Cowork. Standard library only, no network, JSON for every
machine-read file. Mappings that must be deterministic (path → target, change → tests, tracker parsing) live there,
read from the repo's JSON, never hard-coded and never restated in a skill.

## Guards

`hooks/hooks.json` runs `stackfoundry guard` before `Edit`/`Write`/`MultiEdit`/`NotebookEdit` and before
`Bash`/`PowerShell` (the other assistants' hook files run the same command with `--client`; where one cannot ask,
an ask becomes a deny that says to get the user's go-ahead). It reads `.stackfoundry/guards.json`: generated-code globs that may not be hand-edited,
command patterns that are forbidden (direct database writes, raw service launches), and the git-write policy. No
profile means no opinion: the hook exits 0.

- **Git and gh writes:** `scripts/stackfoundry/shellwords.py` parses a command into argv per simple command before
  judging it. It splits on separators, unwraps `sh -c`, `pwsh -Command`, `cmd /c` and `$(…)`, and drops wrappers
  and `VAR=x` prefixes. Global options such as `-C`, `-c` and `--no-pager` are skipped, and path-prefixed or `.exe`
  programs are recognised. Reads (`git config --get`, `gh api` without fields) stay reads.
- **Coverage:** a command that can't be split, such as one with unbalanced quotes, falls back to the old
  whole-string patterns. The guard prevents accidents; it is not a security boundary.
- **Nested files:** every `guards.json` from the call's folder up, plus the project root's, applies at once, and the
  strictest answer wins (`guard.py` `_chain`, `verdict`).
  - An edit is denied when any file's `generated` glob matches it, relative to that file's root.
  - Commands take the strictest matching rule, and `git.writes` the strictest policy.
  - A worktree, sample project or fixture adds its own rules, and an empty or broken nested file is skipped. Neither
    can lift the rules above it.

## Product direction

`whats-next` points a team at its next product and technical steps for any kind of product. Three files make it
generic without shipping any domain knowledge:

- `.stackfoundry/product.json` says what kind of product this is (category, audiences, markets, stage, goals). The
  surveyor infers it from what the code is about, init confirms it, `sync` notices when the product outgrows it.
- `.stackfoundry/domain/<domainId>.json` is a **domain brief**: what a product of that kind is expected to offer
  (table stakes, expected, differentiators), the regulations of its markets, its metrics, how such products
  usually fail and where the domain moves. Like a pack, it is researched from current sources by an agent
  (`domain-researcher`, procedure `reference/product-research.md`), every item cited, and refreshed when it ages or
  the product's scope moves. It describes the domain, not this repo, so the same brief serves any product of the
  kind.
- The audit is per run: `product-analyst` agents mark each capability present, partial, planned or missing with
  path evidence, and the skill adds the technical picture from what the repo already tracks (findings, threat
  models, radar and dependency reports, untested hot areas). Items are ranked by risk and value weighted by the
  targets' stakes, every one with a domain source and a repo path; picked items become backlog plans.

The plugin ships the method (schemas, the research procedure, the ranking), never a list of features for any
domain: that list would be stale and generic, which is exactly what a researched, cited brief avoids.

## Scheduled skills

Unattended skills (`check-updates`, `tech-radar`, `stackfoundry-radar`, `flaky-watch`, report-only `docs-reconciler`
and `whats-next`) follow one contract: no questions, no installs, no git writes, exactly one output file, and a `git status` comparison
that lists any side effect in the report. Their interactive consumers (`act-on-updates`, `act-on-radar`) ask once,
then dispatch each item to the skill that owns it.

`/stackfoundry:schedule` registers them as Claude desktop scheduled tasks, which run on your machine with your
toolchain (needed for `npm outdated`, `dotnet list package`, …) and catch up missed runs. `claude -p` with the OS
scheduler and GitHub Actions (`claude-code-action` with the marketplace and plugin inputs) are documented
alternatives. Cloud routines suit only the web-research skills, since they clone fresh and may not load
repo-enabled plugins.

## Upgrades

Every file `init` generates records, in `.stackfoundry/manifest.lock.json`, the template it came from, the
template version and the hash it had when written. `upgrade` regenerates from the new template and sorts each file
into: untouched since generation (replace), edited by the team (three-way proposal, never applied silently),
materialized (a real three-way merge, below), or deleted by the team (leave deleted).

## Extending without forking

Teams change the plugin's skills and agents; editing the installed plugin is lost on the next marketplace update,
and a same-named skill in the repo does not replace a namespaced plugin skill (and precedence differs between
assistants). So the change lives in a file the repo owns, `.stackfoundry/extensions/skills/<skill>.md` or
`agents/<role>.md`, and the plugin reads it: the shared preamble tells every skill and agent to Read its extension
before step 1. That is only a file read, so it works in every assistant.

- **`extend`** files add anchored sections (`## Rules`, `## Before:`/`After:`/`Replace:` a step, `## Target:`); the
  plugin's own text keeps arriving with every update.
- **`replace`** files and materialized agents are whole copies. Each is stored with the plugin text it came from
  (`.stackfoundry/extensions/.base/`), so `upgrade` runs a real three-way merge (`git merge-file`) and asks only
  about a conflict, instead of freezing the copy.
- **Anchors are step headings and numbered bold step labels.** Renaming one is a changelog item ("Changed
  (extension anchors)"); `extensions check`, `upgrade` and `stackfoundry-radar` find orphaned anchors.
- **A fixed contract** (confirmations, guards, git policy, brief fields, report and tracker shape, severity and
  verdict words) holds over every extension, because other skills parse those outputs.

`customize` writes extensions; `walkthrough` mentions it for every skill it explains. The format is
`plugins/stackfoundry/reference/extensions.md`.

## Testing the plugin

- `tests/`: unittest suite for the CLI and the hooks.
- `fixtures/`: scaffold scripts that build small repos, each with a planted bug, a weak test and an outdated pinned
  package. `dotnet-web-and-wpf` exists to prove that two app models on one language become two stacks.
- `plugins/stackfoundry/evals/`: `claude plugin eval` cases, scored with and without the plugin.

## Not yet

- Splitting into several plugins (quality, deps, docs, radar…). The families call each other, and a skill or agent
  in one plugin calling one in another is not documented, so v1 is one plugin until a spike proves it works.
- A generic dev runtime (service registry, locks, worktree slots with port offsets) driven by a services file.
