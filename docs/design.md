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

The plugin ships the **method**: the layer taxonomy, the schemas, the research procedure, the role briefs and the
rulebook and tracker templates. It ships no rules about any particular technology. `init` researches each detected
technology from current official sources (release notes, migration guides, security advisories, framework docs) and
writes the pack into the repo with every claim citing a URL, a version and an access date. `tech-radar` re-researches
packs older than the refresh window or behind the version the repo now uses.

Why: a shipped rule about a framework is stale the day the framework ships its next major, and it reads as
authoritative. A researched rule carries its source and date, so its age is visible and refreshable.

## Procedure in the plugin, facts in the repo

| Plugin | Repo (written by `init`) |
|---|---|
| orchestrator skills | `.claude/stackfoundry/profile.md`: the product, users, risk surfaces, compliance regime, git policy |
| generic role agents | `.claude/stackfoundry/targets.json`: targets, paths, packs, gates, harness, test dirs, exposure, path rules, specialists |
| reference (method) | `.claude/stackfoundry/targets/<target>.md`: stack facts, categories, oracle sources, traps |
| helper CLI and hooks | `.claude/stackfoundry/ecosystems.json`, `guards.json`, `packs/<layer>-<tech>/` |
| | `.claude/rules/<layer>-<tech>.md`, `.claude/skills/<app-model>-code-writer/` |
| | tracker scaffolds under the docs root; `manifest.lock.json` |

Two reasons. Plugins cannot ship path-scoped rules or CLAUDE.md content, so the rules have to be in the repo anyway.
And procedure has to be upgradable: a skill copied into every repo at install time freezes there.

### Role agents

One agent per role (`bug-hunter`, `fix-verifier`, `test-designer`, `test-writer`, `test-reviewer`, `test-fixer`,
`performance-reviewer`, `security-reviewer`, `code-verifier`, …). The orchestrator passes `target`, and the agent
reads that target's profile and rulebooks. Variants exist only where tool grants must differ (`web-fix-verifier` has
the browser tools). Claude Code loads every agent description in each session and warns past a budget, so one agent
per role, instead of one per role × target, is also what keeps the listing small.

`/stackfoundry:materialize <target> <role>` writes a dedicated agent into the repo when a team wants to hand-tune one
(a security-weighted auth server, say). The manifest records it, and `upgrade` leaves it alone.

### Skills that are slash-only

Skills a person starts on purpose (`init`, `sync`, `upgrade`, the plan modes, the `act-on-*` skills, `quality-sweep`,
`github-prs`, `cleanup-merged`, `schedule`) set `disable-model-invocation: true`. That keeps their descriptions out of
the skill listing, which gets a fixed share of the context window, and leaves room for the skills Claude should pick
on its own.

## The helper CLI

`plugins/stackfoundry/bin/stackfoundry` is a POSIX `sh` launcher that finds Python 3.10+ (`python3`, `python`,
`py -3`) and runs `scripts/stackfoundry/cli.py` isolated (`-I`). Standard library only, no network, JSON for every
machine-read file. Mappings that must be deterministic (path → target, change → tests, tracker parsing) live there,
read from the repo's JSON, never hard-coded and never restated in a skill.

## Guards

`hooks/hooks.json` runs `stackfoundry guard` before `Edit`/`Write`/`MultiEdit`/`NotebookEdit` and before
`Bash`/`PowerShell`. It reads `.claude/stackfoundry/guards.json`: generated-code globs that may not be hand-edited,
command patterns that are forbidden (direct database writes, raw service launches), and the git-write policy. No
profile means no opinion: the hook exits 0.

## Scheduled skills

Unattended skills (`check-updates`, `tech-radar`, `stackfoundry-radar`, `flaky-watch`, report-only `docs-reconciler`)
follow one contract: no questions, no installs, no git writes, exactly one output file, and a `git status` comparison
that lists any side effect in the report. Their interactive consumers (`act-on-updates`, `act-on-radar`) ask once,
then dispatch each item to the skill that owns it.

`/stackfoundry:schedule` registers them as Claude desktop scheduled tasks, which run on your machine with your
toolchain (needed for `npm outdated`, `dotnet list package`, …) and catch up missed runs. `claude -p` with the OS
scheduler and GitHub Actions (`claude-code-action` with the marketplace and plugin inputs) are documented
alternatives. Cloud routines suit only the web-research skills, since they clone fresh and may not load
repo-enabled plugins.

## Upgrades

Every file `init` generates records, in `.claude/stackfoundry/manifest.lock.json`, the template it came from, the
template version and the hash it had when written. `upgrade` regenerates from the new template and sorts each file
into: untouched since generation (replace), edited by the team (three-way proposal, never applied silently),
materialized (skip), or deleted by the team (leave deleted).

## Testing the plugin

- `tests/`: unittest suite for the CLI and the hooks.
- `fixtures/`: scaffold scripts that build small repos, each with a planted bug, a weak test and an outdated pinned
  package. `dotnet-web-and-wpf` exists to prove that two app models on one language become two stacks.
- `plugins/stackfoundry/evals/`: `claude plugin eval` cases, scored with and without the plugin.

## Not yet

- Splitting into several plugins (quality, deps, docs, radar…). The families call each other, and a skill or agent
  in one plugin calling one in another is not documented, so v1 is one plugin until a spike proves it works.
- A generic dev runtime (service registry, locks, worktree slots with port offsets) driven by a services file.
